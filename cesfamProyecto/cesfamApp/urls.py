from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Se registran los ViewSets para la API
router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'cesfams', views.CesfamViewSet)
router.register(r'citas', views.CitaViewSet)
router.register(r'servicios', views.ServicioViewSet)
router.register(r'anuncios', views.AnuncioViewSet)
router.register(r'horarios', views.HorarioViewSet)
router.register(r'notificaciones', views.NotificacionViewSet)
router.register(r'system-messages', views.SystemMessageViewSet) # Renamed from 'mensajes'
router.register(r'conversations', views.ConversationViewSet, basename='conversation')
router.register(r'messages', views.MessageViewSet, basename='message')

urlpatterns = [
    path('', include(router.urls)),
    # Nested messages endpoint
    path('conversations/<int:conversation_pk>/messages/', 
         views.MessageViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='conversation-messages-list'),
    path('conversations/<int:conversation_pk>/messages/<int:pk>/', 
         views.MessageViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), 
         name='conversation-messages-detail'),
    path('conversations/<int:conversation_pk>/messages/<int:pk>/mark_as_read/',
         views.MessageViewSet.as_view({'post': 'mark_as_read'}),
         name='conversation-message-mark-as-read'),
]
