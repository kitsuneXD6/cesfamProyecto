from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

# ==============================================================================
# MODELO DE USUARIO PERSONALIZADO
# ==============================================================================
# Este modelo reemplaza a los antiguos modelos 'Usuario' y 'Profesional'.
# Hereda de AbstractUser de Django para un manejo de autenticación seguro.

class CustomUser(AbstractUser):
    """
    Modelo de usuario personalizado que extiende el AbstractUser de Django.
    Incluye un sistema de roles para diferenciar entre 'paciente' y 'profesional'.
    """
    ROL_PACIENTE = 'paciente'
    ROL_PROFESIONAL = 'profesional'
    ROL_ADMIN = 'admin'
    
    ROL_CHOICES = (
        (ROL_PACIENTE, 'Paciente'),
        (ROL_PROFESIONAL, 'Profesional'),
        (ROL_ADMIN, 'Administrador'),
    )
    
    # Campos heredados de AbstractUser que se utilizarán:
    # username, first_name, last_name, email, password,
    # is_staff, is_superuser, date_joined, etc.

    # Nuevos campos para unificar Usuario y Profesional
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default=ROL_PACIENTE, verbose_name="Rol")
    run = models.CharField(max_length=12, unique=True, null=True, blank=True, verbose_name="RUN")
    telefono = models.CharField(max_length=20, null=True, blank=True, verbose_name="Teléfono")

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_rol_display()})"


# ==============================================================================
# MODELOS PRINCIPALES DE LA APLICACIÓN
# ==============================================================================

class Cesfam(models.Model):
    # Se elimina id_cesfam explícito, Django creará un 'id' automáticamente.
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=100)
    # Se cambia telefono a CharField para mayor flexibilidad.
    telefono = models.CharField(max_length=20)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'cesfam'
        verbose_name = "CESFAM"
        verbose_name_plural = "CESFAMs"


class Servicio(models.Model):
    # Se elimina id_servicio explícito.
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=200)
    profesionales = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        limit_choices_to={'rol': CustomUser.ROL_PROFESIONAL},
        related_name='servicios_ofrecidos',
        blank=True,
        verbose_name="Profesionales que ofrecen el servicio"
    )

    def __str__(self):
        return f"{self.nombre} ({self.tipo})"

    class Meta:
        db_table = 'servicio'
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"


class Cita(models.Model):
    # Se elimina id_cita explícito.
    fecha_hora = models.DateTimeField(verbose_name="Fecha y Hora")
    
    # Se usan ForeignKeys al nuevo CustomUser (settings.AUTH_USER_MODEL).
    # Se usan related_name para evitar conflictos en el modelo User.
    paciente = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='citas_como_paciente',
        verbose_name="Paciente"
    )
    profesional = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='citas_como_profesional',
        verbose_name="Profesional"
    )
    cesfam = models.ForeignKey(Cesfam, on_delete=models.CASCADE, verbose_name="CESFAM")
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, verbose_name="Servicio")

    def __str__(self):
        return f"Cita de {self.paciente} con {self.profesional} el {self.fecha_hora.strftime('%d-%m-%Y %H:%M')}"

    class Meta:
        db_table = 'cita'
        verbose_name = "Cita"
        verbose_name_plural = "Citas"


class Horario(models.Model):
    LUNES = 0
    MARTES = 1
    MIERCOLES = 2
    JUEVES = 3
    VIERNES = 4
    SABADO = 5
    DOMINGO = 6

    DIAS_SEMANA = (
        (LUNES, 'Lunes'),
        (MARTES, 'Martes'),
        (MIERCOLES, 'Miércoles'),
        (JUEVES, 'Jueves'),
        (VIERNES, 'Viernes'),
        (SABADO, 'Sábado'),
        (DOMINGO, 'Domingo'),
    )

    profesional = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        limit_choices_to={'rol': CustomUser.ROL_PROFESIONAL},
        verbose_name="Profesional"
    )
    dia = models.IntegerField(choices=DIAS_SEMANA, help_text="Día de la semana en que el profesional atiende")
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    bloqueado = models.BooleanField(default=False)

    def __str__(self):
        return f"Horario de {self.profesional} para el día {self.get_dia_display()}"

    class Meta:
        db_table = 'horario'
        verbose_name = "Horario"
        verbose_name_plural = "Horarios"


# ==============================================================================
# MODELOS DE COMUNICACIÓN
# ==============================================================================

class Anuncio(models.Model):
    # Se elimina id_anuncio explícito.
    publicado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        limit_choices_to={'rol__in': [CustomUser.ROL_PROFESIONAL, CustomUser.ROL_ADMIN]},
        verbose_name="Publicado por"
    )
    titulo = models.CharField(max_length=100)
    contenido = models.TextField()
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.titulo

    class Meta:
        db_table = 'anuncio'
        ordering = ['-fecha_publicacion']
        verbose_name = "Anuncio"
        verbose_name_plural = "Anuncios"


class Notificacion(models.Model):
    # Se elimina id_notificacion explícito.
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        verbose_name="Destinatario"
    )
    mensaje = models.CharField(max_length=255)
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notificación para {self.destinatario}: {self.mensaje[:30]}..."

    class Meta:
        db_table = 'notificacion'
        ordering = ['-fecha']
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"


class Mensaje(models.Model):
    # Se elimina id_mensaje explícito.
    remitente = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='system_mensajes_enviados',
        verbose_name="Remitente"
    )
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='system_mensajes_recibidos',
        verbose_name="Destinatario"
    )
    
    SYSTEM_MESSAGE_TYPE_CHOICES = (
        ('notification', 'Notificación General'),
        ('alert', 'Alerta del Sistema'),
        ('appointment_reminder', 'Recordatorio de Cita'),
        ('system_update', 'Actualización del Sistema'),
        ('other', 'Otro'),
    )
    message_type = models.CharField(max_length=50, choices=SYSTEM_MESSAGE_TYPE_CHOICES, default='notification', verbose_name="Tipo de Mensaje del Sistema")
    
    contenido = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Mensaje de Sistema de {self.remitente} para {self.destinatario} en {self.fecha.strftime('%d-%m-%Y %H:%M')} ({self.message_type})"

    class Meta:
        db_table = 'mensaje' # Keeping the table name as 'mensaje' for now to avoid migration issues.
        ordering = ['-fecha']
        verbose_name = "Mensaje del Sistema"
        verbose_name_plural = "Mensajes del Sistema"

# ==============================================================================
# MODELOS DE CONVERSACIÓN Y MENSAJES (Nuevo para comunicación directa)
# ==============================================================================

class Conversation(models.Model):
    """
    Modelo para agrupar mensajes entre dos o más usuarios.
    """
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations',
        verbose_name="Participantes"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    topic = models.CharField(max_length=255, blank=True, null=True, verbose_name="Asunto de la Conversación")
    
    # Opcional: Relacionar una conversación con una cita específica
    cita = models.ForeignKey(
        Cita,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='conversacion_cita',
        verbose_name="Cita Relacionada"
    )
    
    # Para rastrear qué usuarios han leído el ÚLTIMO mensaje en la conversación
    # (Esto es diferente de que cada mensaje tenga un estado de leído)
    is_read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='read_conversations',
        blank=True,
        verbose_name="Leído por"
    )

    def __str__(self):
        participant_names = ", ".join([user.get_full_name() or user.username for user in self.participants.all()])
        return f"Conversación con {participant_names} (Última actual. {self.updated_at.strftime('%d-%m-%Y %H:%M')})"

    class Meta:
        ordering = ['-updated_at']
        verbose_name = "Conversación"
        verbose_name_plural = "Conversaciones"


class Message(models.Model):
    """
    Modelo para los mensajes individuales dentro de una conversación.
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="Conversación"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name="Remitente"
    )
    content = models.TextField(verbose_name="Contenido del Mensaje")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Fecha/Hora de Envío")
    
    # Para rastrear qué usuarios (de los participantes de la conversación) han leído este mensaje específico
    # Esto es útil para "visto por" individuales.
    read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='read_messages',
        blank=True,
        verbose_name="Leído por"
    )

    def __str__(self):
        return f"Mensaje de {self.sender.username} en '{self.conversation.id}' ({self.timestamp.strftime('%d-%m-%Y %H:%M')})"

    class Meta:
        ordering = ['timestamp']
        verbose_name = "Mensaje"
        verbose_name_plural = "Mensajes"

# ==============================================================================
# MODELOS ADICIONALES ( placeholders )
# ==============================================================================

class HistorialMedico(models.Model):
    """
    Entrada en el historial médico de un paciente.
    """
    paciente = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        limit_choices_to={'rol': CustomUser.ROL_PACIENTE},
        related_name='historial_medico'
    )
    profesional = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        limit_choices_to={'rol': CustomUser.ROL_PROFESIONAL},
        related_name='entradas_historial_creadas'
    )
    fecha = models.DateTimeField(auto_now_add=True)
    entrada = models.TextField(verbose_name="Descripción de la entrada")

    def __str__(self):
        return f"Entrada para {self.paciente} el {self.fecha.strftime('%d-%m-%Y')}"

    class Meta:
        db_table = 'historial_medico'
        ordering = ['-fecha']
        verbose_name = "Entrada de Historial Médico"
        verbose_name_plural = "Historiales Médicos"


class Feedback(models.Model):
    """
    Feedback dejado por un usuario sobre el sistema o el servicio.
    """
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comentario = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback de {self.usuario} el {self.fecha.strftime('%d-%m-%Y')}"
    
    class Meta:
        db_table = 'feedback'
        ordering = ['-fecha']
        verbose_name = "Feedback"
        verbose_name_plural = "Feedbacks"