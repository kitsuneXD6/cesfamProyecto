from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
import requests
import urllib3
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .decorators import paciente_required, profesional_required, admin_required
from .models import CustomUser as User, Cesfam, Cita, Servicio, Anuncio, Horario, Notificacion, Mensaje, Conversation, Message
from .serializers import (
    UserSerializer, CesfamSerializer, CitaSerializer, ServicioSerializer,
    AnuncioSerializer, HorarioSerializer, NotificacionSerializer,
    SystemMessageSerializer, ConversationSerializer, MessageSerializer
)

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    Replaces the old UsuarioViewSet and ProfesionalViewSet.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer

class CesfamViewSet(viewsets.ModelViewSet):
    queryset = Cesfam.objects.all()
    serializer_class = CesfamSerializer

class CitaViewSet(viewsets.ModelViewSet):
    queryset = Cita.objects.all()
    serializer_class = CitaSerializer

class ServicioViewSet(viewsets.ModelViewSet):
    queryset = Servicio.objects.all()
    serializer_class = ServicioSerializer

class AnuncioViewSet(viewsets.ModelViewSet):
    queryset = Anuncio.objects.all()
    serializer_class = AnuncioSerializer

class HorarioViewSet(viewsets.ModelViewSet):
    queryset = Horario.objects.all()
    serializer_class = HorarioSerializer

class NotificacionViewSet(viewsets.ModelViewSet):
    queryset = Notificacion.objects.all()
    serializer_class = NotificacionSerializer

class SystemMessageViewSet(viewsets.ModelViewSet): # Renamed from MensajeViewSet
    """
    API endpoint that allows system messages to be viewed or edited.
    """
    queryset = Mensaje.objects.all() # Mensaje is now the SystemMessage model
    serializer_class = SystemMessageSerializer

class ConversationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows conversations to be viewed or created.
    Users can only see conversations they are part of.
    """
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only return conversations that the current user is a participant of
        return Conversation.objects.filter(participants=self.request.user).order_by('-updated_at')

    def perform_create(self, serializer):
        # When creating a conversation, ensure the requesting user is a participant
        instance = serializer.save()
        instance.participants.add(self.request.user)
        instance.is_read_by.add(self.request.user) # Mark as read by creator

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        conversation = self.get_object()
        conversation.is_read_by.add(request.user)
        return Response({'status': 'conversation marked as read'}, status=status.HTTP_200_OK)

class MessageViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows messages to be viewed, sent, or edited.
    Messages are always associated with a conversation.
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only return messages for conversations the current user is a participant of
        # Filter by conversation if 'conversation_pk' is provided in the URL
        if 'conversation_pk' in self.kwargs:
            return Message.objects.filter(
                conversation__pk=self.kwargs['conversation_pk'],
                conversation__participants=self.request.user
            ).order_by('timestamp')
        
        # Otherwise, return all messages from conversations the user is in
        return Message.objects.filter(conversation__participants=self.request.user).order_by('timestamp')

    def perform_create(self, serializer):
        conversation = serializer.validated_data['conversation']
        # Asegura que el usuario autenticado es participante
        if self.request.user not in conversation.participants.all():
            conversation.participants.add(self.request.user)
        message = serializer.save(sender=self.request.user)
        # Actualiza la fecha de la conversación
        conversation.updated_at = message.timestamp
        conversation.save()
        # Marca como leído por el remitente
        conversation.is_read_by.add(self.request.user)
        # Limpia el estado de leído para otros participantes
        conversation.is_read_by.remove(*[p for p in conversation.participants.all() if p != self.request.user])

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        message = self.get_object()
        if request.user in message.conversation.participants.all():
            message.read_by.add(request.user)
            return Response({'status': 'message marked as read'}, status=status.HTTP_200_OK)
        return Response({'detail': 'User is not a participant of this conversation.'}, status=status.HTTP_403_FORBIDDEN)

    def create(self, request, *args, **kwargs):
        # Si el endpoint es anidado, obtiene conversation_pk de la URL
        conversation_pk = kwargs.get('conversation_pk')
        data = request.data.copy()
        if conversation_pk and not data.get('conversation'):
            data['conversation'] = conversation_pk
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

# ==============================================================================
# FLUJO DE AGENDAMIENTO DE CITAS
# ==============================================================================

@paciente_required
def agendar_cita_paso1(request):
    """Paso 1: Muestra los servicios disponibles para agendar."""
    servicios = Servicio.objects.all()
    context = {
        'servicios': servicios
    }
    return render(request, 'agendamiento/paso1_servicio.html', context)

@paciente_required
def agendar_cita_paso2(request, servicio_id):
    """Paso 2: Muestra los profesionales disponibles para un servicio."""
    # Lógica para filtrar profesionales por servicio (a implementar)
    try:
        servicio = Servicio.objects.get(pk=servicio_id)
    except Servicio.DoesNotExist:
        messages.error(request, 'El servicio seleccionado no existe.')
        return redirect('agendar_cita_paso1')
    
    profesionales = servicio.profesionales.all()
    context = {
        'servicio': servicio,
        'profesionales': profesionales
    }
    return render(request, 'agendamiento/paso2_profesional.html', context)

@paciente_required
def agendar_cita_paso3(request, profesional_id, servicio_id):
    """Paso 3: Muestra los horarios disponibles para un profesional."""
    try:
        profesional = User.objects.get(pk=profesional_id, rol=User.ROL_PROFESIONAL)
        servicio = Servicio.objects.get(pk=servicio_id)
    except (User.DoesNotExist, Servicio.DoesNotExist):
        messages.error(request, 'El profesional o servicio seleccionado no es válido.')
        return redirect('agendar_cita_paso1')

    # --- Lógica para calcular horarios disponibles ---
    horarios_disponibles = []
    duracion_cita_minutos = 30  # Asumimos que cada cita dura 30 minutos
    dias_a_mostrar = 14  # Mostramos disponibilidad para las próximas 2 semanas

    # 1. Obtener horarios y citas existentes del profesional
    horarios_profesional = Horario.objects.filter(profesional=profesional, bloqueado=False)
    citas_futuras = Cita.objects.filter(
        profesional=profesional,
        fecha_hora__gte=timezone.now()
    ).values_list('fecha_hora', flat=True)

    # Convertir los horarios del profesional a un diccionario para acceso rápido.
    # La clave es el número del día de la semana (0=Lunes), que ahora coincide con el modelo.
    horarios_dict = {h.dia: (h.hora_inicio, h.hora_fin) for h in horarios_profesional}

    # 2. Iterar sobre los próximos días y generar bloques de tiempo disponibles
    start_date = timezone.now().date()
    for i in range(dias_a_mostrar):
        current_date = start_date + timedelta(days=i)
        weekday = current_date.weekday() # Esto devuelve 0 para Lunes, 1 para Martes, etc.

        # Si el profesional trabaja ese día de la semana
        if weekday in horarios_dict:
            hora_inicio, hora_fin = horarios_dict[weekday]
            
            # Combinar la fecha actual con la hora de inicio para crear un objeto datetime
            current_slot = datetime.combine(current_date, hora_inicio, tzinfo=timezone.get_current_timezone())
            hora_fin_dt = datetime.combine(current_date, hora_fin, tzinfo=timezone.get_current_timezone())

            # Generar todos los posibles slots dentro del horario laboral
            while current_slot < hora_fin_dt:
                # 3. Verificar si el bloque es válido (es en el futuro y no está ya reservado)
                if current_slot > timezone.now() and current_slot not in citas_futuras:
                    horarios_disponibles.append(current_slot)
                
                # Avanzar al siguiente bloque de tiempo
                current_slot += timedelta(minutes=duracion_cita_minutos)
    
    context = {
        'profesional': profesional,
        'servicio': servicio,
        'horarios_disponibles': horarios_disponibles
    }
    return render(request, 'agendamiento/paso3_horario.html', context)

@paciente_required
def crear_cita(request):
    """Paso final: Valida y crea la cita en la base de datos."""
    if request.method != 'POST':
        return redirect('agendar_cita_paso1')

    try:
        profesional_id = request.POST.get('profesional_id')
        servicio_id = request.POST.get('servicio_id')
        fecha_hora_str = request.POST.get('fecha_hora_cita')

        if not all([profesional_id, servicio_id, fecha_hora_str]):
            messages.error(request, 'Información incompleta para agendar la cita.')
            return redirect('agendar_cita_paso1')

        profesional = User.objects.get(pk=profesional_id, rol=User.ROL_PROFESIONAL)
        servicio = Servicio.objects.get(pk=servicio_id)
        paciente = request.user
        
        # Convertir el string de fecha a un objeto datetime
        fecha_hora_cita = parse_datetime(fecha_hora_str)
        if not fecha_hora_cita:
            raise ValueError("Formato de fecha inválido.")

        # --- Validación de Seguridad Crítica ---
        # 1. ¿La hora de la cita ya pasó?
        if fecha_hora_cita < timezone.now():
            messages.error(request, 'No puedes agendar una cita en el pasado.')
            return redirect('agendar_cita_paso1')

        # 2. ¿Ya existe una cita en ese mismo bloque? (Prevención de race conditions)
        if Cita.objects.filter(profesional=profesional, fecha_hora=fecha_hora_cita).exists():
            messages.error(request, 'El horario seleccionado ya no está disponible. Por favor, elige otro.')
            return redirect('agendar_cita_paso3', profesional_id=profesional.id, servicio_id=servicio.id)
            
        # 3. TODO: Podríamos añadir validación extra para asegurarse que el horario está dentro
        # del Horario laboral del profesional, pero por ahora confiamos en la lógica del paso 3.

        # --- Creación de la Cita ---
        # Asumimos un solo CESFAM o el primero. Esto podría necesitar más lógica en una app real.
        cesfam_instancia = Cesfam.objects.first()
        if not cesfam_instancia:
            messages.error(request, "No hay ningún CESFAM configurado en el sistema.")
            return redirect('agendar_cita_paso1')

        Cita.objects.create(
            paciente=paciente,
            profesional=profesional,
            servicio=servicio,
            fecha_hora=fecha_hora_cita,
            cesfam=cesfam_instancia
        )
        
        messages.success(request, f'¡Tu cita para {servicio.nombre} ha sido agendada con éxito para el {fecha_hora_cita.strftime("%d/%m/%Y a las %H:%M")}!')
        return redirect('dashboard')

    except (User.DoesNotExist, Servicio.DoesNotExist, ValueError) as e:
        messages.error(request, f'Ocurrió un error al procesar tu solicitud: {e}')
        return redirect('agendar_cita_paso1')



# FLUJO DE AGENDAMIENTO POR PROFESIONAL
# ==============================================================================
@login_required
@profesional_required
def profesional_horarios_json(request):
    profesional = request.user
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')

    if not all([start_str, end_str]):
        return JsonResponse({'error': 'Missing start or end parameters'}, status=400)

    try:
        start = parse_datetime(start_str)
        end = parse_datetime(end_str)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    # Lógica para calcular horarios disponibles
    horarios_disponibles = []
    duracion_cita_minutos = 30 

    horarios_profesional = Horario.objects.filter(profesional=profesional, bloqueado=False)
    citas_futuras = Cita.objects.filter(
        profesional=profesional,
        fecha_hora__range=(start, end)
    ).values_list('fecha_hora', flat=True)

    horarios_dict = {h.dia: (h.hora_inicio, h.hora_fin) for h in horarios_profesional}

    current_date = start.date()
    while current_date <= end.date():
        weekday = current_date.weekday()

        if weekday in horarios_dict:
            hora_inicio, hora_fin = horarios_dict[weekday]
            
            current_slot = datetime.combine(current_date, hora_inicio, tzinfo=timezone.get_current_timezone())
            hora_fin_dt = datetime.combine(current_date, hora_fin, tzinfo=timezone.get_current_timezone())

            while current_slot < hora_fin_dt:
                if current_slot > timezone.now() and current_slot not in citas_futuras:
                    horarios_disponibles.append({
                        'title': 'Disponible',
                        'start': current_slot.isoformat(),
                        'end': (current_slot + timedelta(minutes=duracion_cita_minutos)).isoformat(),
                    })
                
                current_slot += timedelta(minutes=duracion_cita_minutos)
        
        current_date += timedelta(days=1)
        
    return JsonResponse(horarios_disponibles, safe=False)

@login_required
@profesional_required
def profesional_agendar(request):
    """
    Página para que un profesional pueda agendar una cita para un paciente.
    """
    profesional = request.user
    pacientes = User.objects.filter(rol=User.ROL_PACIENTE).order_by('first_name', 'last_name')
    
    # Usamos todos los servicios para dar flexibilidad, se podría limitar a `profesional.servicios_ofrecidos.all()`
    servicios = Servicio.objects.all()

    context = {
        'pacientes': pacientes,
        'servicios': servicios,
        'profesional': profesional,
    }
    return render(request, 'agendamiento/profesional_agendar.html', context)


@login_required
@profesional_required
def profesional_crear_cita(request):
    """
    Procesa el formulario enviado por el profesional para crear una cita.
    """
    if request.method != 'POST':
        messages.error(request, 'Método no permitido.')
        return redirect('profesional_agendar')

    try:
        paciente_id = request.POST.get('paciente_id')
        servicio_id = request.POST.get('servicio_id')
        fecha_hora_str = request.POST.get('fecha_hora_cita')

        if not all([paciente_id, servicio_id, fecha_hora_str]):
            messages.error(request, 'Información incompleta. Debes seleccionar paciente, servicio y horario.')
            return redirect('profesional_agendar')

        profesional = request.user
        paciente = User.objects.get(pk=paciente_id, rol=User.ROL_PACIENTE)
        servicio = Servicio.objects.get(pk=servicio_id)
        
        fecha_hora_cita = parse_datetime(fecha_hora_str)
        if not fecha_hora_cita:
            raise ValueError("Formato de fecha inválido.")

        if fecha_hora_cita < timezone.now():
            messages.error(request, 'No puedes agendar una cita en el pasado.')
            return redirect('profesional_agendar')

        if Cita.objects.filter(profesional=profesional, fecha_hora=fecha_hora_cita).exists():
            messages.error(request, 'Ya tienes una cita en ese horario. Por favor, elige otro.')
            return redirect('profesional_agendar')
        
        if Cita.objects.filter(paciente=paciente, fecha_hora=fecha_hora_cita).exists():
            messages.warning(request, f'Advertencia: El paciente {paciente.first_name} ya tiene otra cita en ese mismo horario.')

        cesfam_instancia = Cesfam.objects.first()
        if not cesfam_instancia:
            messages.error(request, "No hay ningún CESFAM configurado en el sistema.")
            return redirect('profesional_agendar')

        # Crear la cita
        nueva_cita = Cita.objects.create(
            paciente=paciente,
            profesional=profesional,
            servicio=servicio,
            fecha_hora=fecha_hora_cita,
            cesfam=cesfam_instancia
        )
        
        # Crear notificación para el paciente
        Notificacion.objects.create(
            destinatario=paciente,
            mensaje=f'El profesional {profesional.get_full_name()} te ha agendado una cita para el {fecha_hora_cita.strftime("%d/%m a las %H:%Mh")}.'
        )
        
        messages.success(request, f'Cita para {paciente.get_full_name()} agendada con éxito.')
        return redirect('dashboard')

    except (User.DoesNotExist, Servicio.DoesNotExist):
        messages.error(request, 'El paciente o servicio seleccionado no es válido.')
        return redirect('profesional_agendar')
    except ValueError as e:
        messages.error(request, f'Ocurrió un error al procesar la fecha: {e}')
        return redirect('profesional_agendar')
    except Exception as e:
        messages.error(request, f'Ocurrió un error inesperado: {e}')
        return redirect('profesional_agendar')

def farmacias_turno(request):
    todas_las_comunas = []
    try:
        # Workaround for DNS issue in Render: Use direct IP and Host header
        url = "https://162.215.243.194/maps/index.php/ws/getLocalesTurnos"
        headers = {'Host': 'farmanet.minsal.cl'}
        print("INFO: Intentando conexión con 'verify=False' y timeout=30s...")
        # verify=False es el último recurso para problemas de red/SSL en Render.
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        response.raise_for_status()
        farmacias = response.json()
        print("INFO: Conexión y decodificación de JSON exitosa.")
        
        if farmacias:
            todas_las_comunas = sorted(list(set(f['comuna_nombre'] for f in farmacias)))

        comuna = request.GET.get('comuna', '').lower()
        if comuna:
            farmacias = [f for f in farmacias if f['comuna_nombre'].lower() == comuna]
            
    except requests.exceptions.Timeout as e:
        print(f"ERROR: Timeout al conectar con la API de farmacias: {e}")
        messages.error(request, "El servicio de farmacias tardó demasiado en responder. Inténtalo de nuevo más tarde.")
        farmacias = []
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Error de conexión/request al llamar a la API de farmacias: {e}")
        messages.error(request, f"Error al contactar el servicio de farmacias. Es posible que el servicio no esté disponible o haya un problema de red.")
        farmacias = []
    except ValueError as e:
        print(f"ERROR: Error al decodificar la respuesta JSON de la API: {e}")
        messages.error(request, "Error al procesar la respuesta del servicio de farmacias.")
        farmacias = []
    
    context = {
        'farmacias': farmacias, 
        'comuna': request.GET.get('comuna', ''),
        'todas_las_comunas': todas_las_comunas
    }
    return render(request, 'farmacias_turno.html', context)

def home(request):
    """Vista principal de bienvenida."""
    return render(request, 'inicio.html')

def login_page(request):
    return render(request, 'login_page.html')

def logout_view(request):
    # Puedes agregar lógica de logout real luego
    return redirect('home')

def register_page(request):
    return render(request, 'register_page.html')

def register_select(request):
    return render(request, 'register_select.html')

def register_usuario(request):
    return render(request, 'register_usuario.html')

def register_profesional(request):
    if request.method == 'POST':
        # Extraer datos del formulario
        first_name = request.POST.get('nombre')
        last_name = request.POST.get('apellido')
        email = request.POST.get('email')
        password = request.POST.get('password')
        servicios_ids = request.POST.getlist('servicios')

        # Validación básica
        if not all([first_name, last_name, email, password, servicios_ids]):
            messages.error(request, 'Todos los campos son obligatorios.')
            servicios = Servicio.objects.all()
            return render(request, 'register_profesional.html', {'servicios': servicios})

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Ya existe un usuario con este correo electrónico.')
            servicios = Servicio.objects.all()
            return render(request, 'register_profesional.html', {'servicios': servicios})

        try:
            # Crear usuario (el username será el email)
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                rol=User.ROL_PROFESIONAL
            )

            # Asignar servicios
            servicios = Servicio.objects.filter(id__in=servicios_ids)
            user.servicios_ofrecidos.set(servicios)

            # Iniciar sesión y redirigir
            login(request, user)
            messages.success(request, '¡Registro completado con éxito! Has iniciado sesión.')
            return redirect('dashboard')

        except Exception as e:
            messages.error(request, f'Ocurrió un error durante el registro: {e}')
            servicios = Servicio.objects.all()
            return render(request, 'register_profesional.html', {'servicios': servicios})

    else: # GET request
        servicios = Servicio.objects.all()
        context = {
            'servicios': servicios
        }
        return render(request, 'register_profesional.html', context)

def register_admin(request):
    return render(request, 'register_admin.html')

def dashboard(request):
    return render(request, 'dashboard.html')

def profile_view(request):
    return render(request, 'perfil.html')

def dashboard_metricas(request):
    return render(request, 'dashboard_metricas.html')

def modal_test(request):
    return render(request, 'modal_test.html')

def cancelar_cita(request):
    # Lógica real se puede agregar después
    return redirect('dashboard')

def marcar_atendida(request):
    return redirect('dashboard')

def ayuda(request):
    return render(request, 'ayuda.html')

def mensaje(request):
    return render(request, 'mensaje.html')

def mensajeria(request):
    return render(request, 'mensajes.html')

def historial_medico(request):
    return render(request, 'historial_medico.html')

def notificacion(request):
    return render(request, 'notificacion.html')

def horario(request):
    return render(request, 'horario.html')

def feedback(request):
    return render(request, 'feedback.html')

def gestionar_anuncios(request):
    return render(request, 'gestionar_anuncios.html')

def gestionar_usuarios(request):
    return render(request, 'gestionar_usuarios.html')

def gestionar_profesionales(request):
    return render(request, 'gestionar_profesionales.html')

def supervisar_agendas(request):
    return render(request, 'supervisar_agendas.html')

def gestionar_servicios(request):
    return render(request, 'gestionar_servicios.html')