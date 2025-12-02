from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.utils import timezone

from .models import Conversation, Message, Cita, Servicio, Cesfam

User = get_user_model()

class CommunicationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = 'testpassword123'

        # Create different types of users
        self.patient_user = User.objects.create_user(
            username='patient1', email='patient1@example.com', password=self.password,
            first_name='John', last_name='Doe', rol=User.ROL_PACIENTE
        )
        self.professional_user = User.objects.create_user(
            username='prof1', email='prof1@example.com', password=self.password,
            first_name='Jane', last_name='Smith', rol=User.ROL_PROFESIONAL,
            especialidad='Cardiología'
        )
        self.admin_user = User.objects.create_user(
            username='admin1', email='admin1@example.com', password=self.password,
            first_name='Admin', last_name='User', rol=User.ROL_ADMIN, is_staff=True
        )
        self.other_user = User.objects.create_user(
            username='otheruser', email='other@example.com', password=self.password,
            first_name='Other', last_name='Guy', rol=User.ROL_PACIENTE
        )

        # Create a Cesfam (needed for Cita)
        self.cesfam = Cesfam.objects.create(nombre="Cesfam Test", direccion="123 Test St", telefono="123456789")

        # Create a Servicio (needed for Cita)
        self.servicio = Servicio.objects.create(nombre="Consulta General", tipo="Médica", descripcion="Consulta de rutina")

        # Create a Cita (optional for Conversation linking)
        self.cita = Cita.objects.create(
            fecha_hora=timezone.now() + timedelta(days=7),
            paciente=self.patient_user,
            profesional=self.professional_user,
            cesfam=self.cesfam,
            servicio=self.servicio
        )

        # URLs for API endpoints
        self.conversations_list_url = reverse('conversation-list') # Assumes 'conversation' basename
        self.messages_list_url_template = 'conversations/{}/messages/' # This needs to be built with pk
        
    def _get_messages_list_url(self, conversation_pk):
        return reverse('conversation-messages-list', kwargs={'conversation_pk': conversation_pk})

    def _get_conversation_detail_url(self, pk):
        return reverse('conversation-detail', kwargs={'pk': pk})

    # ==========================================================================
    # CONVERSATION TESTS
    # ==========================================================================

    def test_create_conversation(self):
        self.client.login(username=self.patient_user.username, password=self.password)
        data = {
            'participants_ids': [self.patient_user.id, self.professional_user.id],
            'topic': 'Consulta sobre cita',
            'cita_id': self.cita.id
        }
        response = self.client.post(self.conversations_list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Conversation.objects.count(), 1)
        conversation = Conversation.objects.first()
        self.assertIn(self.patient_user, conversation.participants.all())
        self.assertIn(self.professional_user, conversation.participants.all())
        self.assertEqual(conversation.topic, 'Consulta sobre cita')
        self.assertEqual(conversation.cita, self.cita)
        self.assertIn(self.patient_user, conversation.is_read_by.all()) # Creator should mark it as read

    def test_list_user_conversations(self):
        # Create conversations
        conv1 = Conversation.objects.create(topic='Conv 1')
        conv1.participants.add(self.patient_user, self.professional_user)
        conv2 = Conversation.objects.create(topic='Conv 2')
        conv2.participants.add(self.professional_user, self.admin_user)

        self.client.login(username=self.patient_user.username, password=self.password)
        response = self.client.get(self.conversations_list_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], conv1.id)

        self.client.login(username=self.professional_user.username, password=self.password)
        response = self.client.get(self.conversations_list_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # Should see conv1 and conv2

    def test_retrieve_conversation(self):
        conv = Conversation.objects.create(topic='Test Retrieve')
        conv.participants.add(self.patient_user, self.professional_user)

        self.client.login(username=self.patient_user.username, password=self.password)
        response = self.client.get(self._get_conversation_detail_url(conv.id), format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], conv.id)
        self.assertEqual(response.data['topic'], 'Test Retrieve')

    def test_non_participant_cannot_view_conversation(self):
        conv = Conversation.objects.create(topic='Private Conv')
        conv.participants.add(self.patient_user, self.professional_user)

        self.client.login(username=self.other_user.username, password=self.password)
        response = self.client.get(self._get_conversation_detail_url(conv.id), format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) # DRF returns 404 for objects not in queryset

    def test_mark_conversation_as_read(self):
        conv = Conversation.objects.create(topic='Mark Read Test')
        conv.participants.add(self.patient_user, self.professional_user)
        conv.is_read_by.add(self.professional_user) # Prof has read it, patient hasn't

        self.client.login(username=self.patient_user.username, password=self.password)
        url = reverse('conversation-mark-as-read', kwargs={'pk': conv.id})
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        conv.refresh_from_db()
        self.assertIn(self.patient_user, conv.is_read_by.all())

    # ==========================================================================
    # MESSAGE TESTS
    # ==========================================================================

    def test_send_message(self):
        conv = Conversation.objects.create(topic='Message Test')
        conv.participants.add(self.patient_user, self.professional_user)

        self.client.login(username=self.patient_user.username, password=self.password)
        data = {
            'conversation': conv.id,
            'content': 'Hello professional!'
        }
        response = self.client.post(self._get_messages_list_url(conv.id), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 1)
        message = Message.objects.first()
        self.assertEqual(message.content, 'Hello professional!')
        self.assertEqual(message.sender, self.patient_user)
        self.assertEqual(message.conversation, conv)
        
        # Check conversation updated_at
        conv.refresh_from_db()
        self.assertAlmostEqual(conv.updated_at, message.timestamp, delta=timedelta(seconds=1))
        # Check is_read_by for conversation
        self.assertIn(self.patient_user, conv.is_read_by.all())
        self.assertNotIn(self.professional_user, conv.is_read_by.all())


    def test_list_conversation_messages(self):
        conv = Conversation.objects.create(topic='List Messages')
        conv.participants.add(self.patient_user, self.professional_user)
        Message.objects.create(conversation=conv, sender=self.patient_user, content='Msg 1')
        Message.objects.create(conversation=conv, sender=self.professional_user, content='Msg 2')

        self.client.login(username=self.patient_user.username, password=self.password)
        response = self.client.get(self._get_messages_list_url(conv.id), format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['content'], 'Msg 1')
        self.assertEqual(response.data[1]['content'], 'Msg 2')

    def test_message_sender_automatically_set(self):
        conv = Conversation.objects.create(topic='Auto Sender')
        conv.participants.add(self.patient_user, self.professional_user)

        self.client.login(username=self.patient_user.username, password=self.password)
        data = {
            'conversation': conv.id,
            'content': 'Message from patient',
            'sender_id': self.other_user.id # Attempt to set wrong sender
        }
        response = self.client.post(self._get_messages_list_url(conv.id), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        message = Message.objects.first()
        self.assertEqual(message.sender, self.patient_user) # Should be patient_user, not other_user

    def test_conversation_updated_at_on_new_message(self):
        conv = Conversation.objects.create(topic='Updated At Test', updated_at=timezone.now() - timedelta(days=1))
        conv.participants.add(self.patient_user, self.professional_user)
        old_updated_at = conv.updated_at

        self.client.login(username=self.professional_user.username, password=self.password)
        data = {
            'conversation': conv.id,
            'content': 'New message for update check'
        }
        response = self.client.post(self._get_messages_list_url(conv.id), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        conv.refresh_from_db()
        self.assertGreater(conv.updated_at, old_updated_at)
        self.assertIn(self.professional_user, conv.is_read_by.all())
        self.assertNotIn(self.patient_user, conv.is_read_by.all()) # Patient hasn't read it yet

    def test_non_participant_cannot_send_message(self):
        conv = Conversation.objects.create(topic='Restricted Message')
        conv.participants.add(self.patient_user, self.professional_user)

        self.client.login(username=self.other_user.username, password=self.password)
        data = {
            'conversation': conv.id,
            'content': 'I am not a participant.'
        }
        response = self.client.post(self._get_messages_list_url(conv.id), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Message.objects.count(), 0)

    def test_mark_message_as_read(self):
        conv = Conversation.objects.create(topic='Mark Message Read')
        conv.participants.add(self.patient_user, self.professional_user)
        message = Message.objects.create(conversation=conv, sender=self.professional_user, content='Read this!')

        self.client.login(username=self.patient_user.username, password=self.password)
        url = reverse('conversation-message-mark-as-read', kwargs={'conversation_pk': conv.id, 'pk': message.id})
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        message.refresh_from_db()
        self.assertIn(self.patient_user, message.read_by.all())