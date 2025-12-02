from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Cesfam, Servicio, Cita, Horario, Anuncio, Notificacion, Mensaje, HistorialMedico, Feedback

# --- Admin Personalizado para el Modelo CustomUser ---

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Define la vista de admin para el modelo CustomUser.
    Hereda de UserAdmin para mantener toda la funcionalidad de Django (manejo de contraseñas, etc.)
    y añade los campos personalizados.
    """
    # Campos a mostrar en la lista de usuarios
    list_display = ('username', 'email', 'first_name', 'last_name', 'rol', 'is_staff')
    
    # Filtros para la lista de usuarios
    list_filter = ('rol', 'is_staff', 'is_superuser', 'groups')
    
    # Campos de búsqueda
    search_fields = ('username', 'first_name', 'last_name', 'email', 'run')
    
    # Orden
    ordering = ('username',)

    # Se necesita sobreescribir los fieldsets para añadir los campos personalizados en el
    # formulario de edición de usuario.
    # Copiamos los fieldsets originales de UserAdmin y añadimos los nuestros.
    fieldsets = UserAdmin.fieldsets + (
        ('Información Adicional', {
            'fields': ('rol', 'run', 'telefono', 'especialidad'),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información Adicional', {
            'fields': ('first_name', 'last_name', 'rol', 'run', 'telefono', 'especialidad'),
        }),
    )


# --- Registros Simples para los otros modelos ---

@admin.register(Cesfam)
class CesfamAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion', 'telefono')
    search_fields = ('nombre',)

@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo')
    search_fields = ('nombre', 'tipo')
    filter_horizontal = ('profesionales',)

@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('fecha_hora', 'paciente', 'profesional', 'servicio', 'cesfam')
    list_filter = ('cesfam', 'servicio', 'profesional')
    search_fields = ('paciente__username', 'profesional__username')
    autocomplete_fields = ['paciente', 'profesional', 'cesfam', 'servicio']

@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ('profesional', 'dia', 'hora_inicio', 'hora_fin', 'bloqueado')
    list_filter = ('dia', 'bloqueado', 'profesional')
    search_fields = ('profesional__username',)

@admin.register(Anuncio)
class AnuncioAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'publicado_por', 'fecha_publicacion')
    list_filter = ('fecha_publicacion', 'publicado_por')
    search_fields = ('titulo', 'contenido')

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('destinatario', 'mensaje', 'leida', 'fecha')
    list_filter = ('leida', 'fecha')
    search_fields = ('destinatario__username', 'mensaje')

@admin.register(Mensaje)
class MensajeAdmin(admin.ModelAdmin):
    list_display = ('remitente', 'destinatario', 'fecha', 'leido')
    list_filter = ('leido', 'fecha')
    search_fields = ('remitente__username', 'destinatario__username', 'contenido')

@admin.register(HistorialMedico)
class HistorialMedicoAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'profesional', 'fecha')
    list_filter = ('fecha', 'profesional')
    search_fields = ('paciente__username', 'profesional__username', 'entrada')
    autocomplete_fields = ['paciente', 'profesional']

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'fecha')
    list_filter = ('fecha',)
    search_fields = ('usuario__username', 'comentario')
    autocomplete_fields = ['usuario']