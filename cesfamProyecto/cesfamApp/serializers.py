from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Cesfam, Servicio, Cita, Horario, Anuncio, Notificacion, Mensaje, Conversation, Message

User = get_user_model()

# ==============================================================================
# SERIALIZER PARA EL MODELO DE USUARIO
# ==============================================================================

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo CustomUser.
    Reemplaza a los antiguos UsuarioSerializer y ProfesionalSerializer.
    """
    servicios_ofrecidos = ServicioSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email', 'rol',
            'run', 'telefono', 'is_staff', 'password', 'servicios_ofrecidos'
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 8},
        }

    def create(self, validated_data):
        # El viewset debe pasar el request en el contexto del serializador.
        # Extraemos 'servicios' del POST request original, que puede ser una lista de IDs.
        servicios_ids = self.context['request'].data.getlist('servicios')
        
        # Usamos create_user para hashear la contraseña correctamente.
        user = User.objects.create_user(**validated_data)

        # Si se proporcionaron IDs de servicio, los asociamos al nuevo usuario.
        if servicios_ids:
            # Filtramos para obtener los objetos Servicio válidos
            servicios = Servicio.objects.filter(id__in=servicios_ids)
            user.servicios_ofrecidos.set(servicios)
            
        return user

# ==============================================================================
# SERIALIZERS PARA LOS OTROS MODELOS (ACTUALIZADOS)
# ==============================================================================

class CesfamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cesfam
        fields = '__all__'

class ServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servicio
        fields = '__all__'

class CitaSerializer(serializers.ModelSerializer):
    # Usamos StringRelatedField para una representación legible de los ForeignKeys.
    # En lugar de solo el ID, mostrará el resultado del __str__ del modelo relacionado.
    paciente = serializers.StringRelatedField(read_only=True)
    profesional = serializers.StringRelatedField(read_only=True)
    servicio = serializers.StringRelatedField(read_only=True)
    cesfam = serializers.StringRelatedField(read_only=True)

    # Si quisiéramos poder asignar por ID al crear/actualizar, necesitaríamos campos adicionales.
    paciente_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='paciente', write_only=True)
    profesional_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(rol=User.ROL_PROFESIONAL), source='profesional', write_only=True)
    servicio_id = serializers.PrimaryKeyRelatedField(queryset=Servicio.objects.all(), source='servicio', write_only=True)
    cesfam_id = serializers.PrimaryKeyRelatedField(queryset=Cesfam.objects.all(), source='cesfam', write_only=True)

    class Meta:
        model = Cita
        fields = [
            'id', 'fecha_hora', 'paciente', 'profesional', 'servicio', 'cesfam',
            'paciente_id', 'profesional_id', 'servicio_id', 'cesfam_id'
        ]

class HorarioSerializer(serializers.ModelSerializer):
    profesional = serializers.StringRelatedField(read_only=True)
    profesional_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(rol=User.ROL_PROFESIONAL), source='profesional', write_only=True)

    class Meta:
        model = Horario
        fields = '__all__'

class AnuncioSerializer(serializers.ModelSerializer):
    publicado_por = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Anuncio
        fields = '__all__'

class NotificacionSerializer(serializers.ModelSerializer):
    destinatario = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Notificacion
        fields = '__all__'

class SystemMessageSerializer(serializers.ModelSerializer): # Renamed from MensajeSerializer
    remitente = serializers.StringRelatedField(read_only=True)
    destinatario = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Mensaje # This is the renamed Mensaje model, now SystemMessage
        fields = '__all__'

# ==============================================================================
# SERIALIZERS PARA LOS NUEVOS MODELOS DE COMUNICACIÓN
# ==============================================================================

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True) # Nested serializer for read operations
    sender_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='sender', write_only=True)
    read_by = UserSerializer(many=True, read_only=True) # To show who has read it

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'sender_id', 'content', 'timestamp', 'read_by']
        read_only_fields = ['timestamp']

class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True) # Nested serializer for read operations
    participants_ids = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True, source='participants', write_only=True)
    messages = MessageSerializer(many=True, read_only=True) # Nested serializer to show messages within a conversation
    cita = serializers.StringRelatedField(read_only=True) # Show cita details if available
    cita_id = serializers.PrimaryKeyRelatedField(queryset=Cita.objects.all(), source='cita', write_only=True, required=False, allow_null=True)
    is_read_by = UserSerializer(many=True, read_only=True) # To show who has read the latest message

    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'participants_ids', 'created_at', 'updated_at', 'topic', 'cita', 'cita_id', 'messages', 'is_read_by']
        read_only_fields = ['created_at', 'updated_at']