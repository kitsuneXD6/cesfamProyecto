"""
URL configuration for cesfamProyecto project.
"""
from django.contrib import admin
from django.urls import path, include
from cesfamApp import views

urlpatterns = [
    # API URLs - Temporalmente deshabilitadas, el router está vacío en cesfamApp.urls
    path('api/', include('cesfamApp.urls')),
    
    # Rutas principales de la aplicación
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    
    # Autenticación
    path('login/', views.login_page, name='login_page'), # Renombrada de login_view
    path('logout/', views.logout_view, name='logout'),
    
    # Registro
    path('register/', views.register_page, name='register_page'), # Renombrada de register_view
    path('register/select/', views.register_select, name='register_select'),
    path('register/usuario/', views.register_usuario, name='register_usuario'),
    path('register/profesional/', views.register_profesional, name='register_profesional'),
    path('register/admin/', views.register_admin, name='register_admin'), # Apunta a una vista deshabilitada por seguridad
    
    # Dashboards y vistas de usuario
    path('dashboard/', views.dashboard, name='dashboard'),
    path('perfil/', views.profile_view, name='profile'),
    path('dashboard/metricas/', views.dashboard_metricas, name='dashboard_metricas'),

    # Flujo de Agendamiento de Citas
    path('agendar/', views.agendar_cita_paso1, name='agendar_cita_paso1'),
    path('agendar/profesionales/<int:servicio_id>/', views.agendar_cita_paso2, name='agendar_cita_paso2'),
    path('agendar/horario/<int:profesional_id>/<int:servicio_id>/', views.agendar_cita_paso3, name='agendar_cita_paso3'),
    path('agendar/crear/', views.crear_cita, name='crear_cita'),

    # Flujo de Agendamiento por Profesional
    path('profesional/agendar/', views.profesional_agendar, name='profesional_agendar'),
    path('profesional/horarios/', views.profesional_horarios_json, name='profesional_horarios_json'),
    path('profesional/crear-cita/', views.profesional_crear_cita, name='profesional_crear_cita'),
    
    
    # Otras vistas (algunas necesitan refactorización)
    path('modal-test/', views.modal_test, name='modal_test'),
    path('citas/cancelar/', views.cancelar_cita, name='cancelar_cita'),
    path('citas/atendida/', views.marcar_atendida, name='marcar_atendida'),
    path('ayuda/', views.ayuda, name='ayuda'),
    path('mensajes/', views.mensaje, name='mensaje'),
    path('mensajeria/', views.mensajeria, name='mensajeria'),
    path('historial-medico/', views.historial_medico, name='historial_medico'), # Apunta a vista en construcción
    path('notificaciones/', views.notificacion, name='notificacion'),
    path('horarios/', views.horario, name='horario'),
    path('feedback/', views.feedback, name='feedback'), # Apunta a vista en construcción
    
    # Vistas de Administración (idealmente se reemplazan con el admin de Django)
    path('admin/anuncios/', views.gestionar_anuncios, name='gestionar_anuncios'),
    path('admin/usuarios/', views.gestionar_usuarios, name='gestionar_usuarios'),
    path('admin/profesionales/', views.gestionar_profesionales, name='gestionar_profesionales'),
    path('admin/agendas/', views.supervisar_agendas, name='supervisar_agendas'),
    path('admin/servicios/', views.gestionar_servicios, name='gestionar_servicios'),
    
    # Ruta para farmacias de turno
    path('farmacias-turno/', views.farmacias_turno, name='farmacias_turno'),
]