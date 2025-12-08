# cesfamProyecto/cesfamApp/management/commands/poblar_horarios.py

from django.core.management.base import BaseCommand
from cesfamApp.models import CustomUser, Horario
import time

class Command(BaseCommand):
    help = 'Puebla la base de datos con horarios de ejemplo para los profesionales existentes.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Iniciando poblado de horarios ---'))

        # 1. Obtener todos los usuarios que son profesionales
        profesionales = CustomUser.objects.filter(rol=CustomUser.ROL_PROFESIONAL)

        if not profesionales.exists():
            self.stdout.write(self.style.WARNING('No se encontraron profesionales en la base de datos. No se crearán horarios.'))
            return

        self.stdout.write(f'Se encontraron {profesionales.count()} profesionales.')

        # 2. Definir un horario estándar de Lunes a Viernes
        horario_estandar = [
            # Mañana
            {'dia': Horario.LUNES, 'inicio': time(9, 0), 'fin': time(13, 0)},
            {'dia': Horario.MARTES, 'inicio': time(9, 0), 'fin': time(13, 0)},
            {'dia': Horario.MIERCOLES, 'inicio': time(9, 0), 'fin': time(13, 0)},
            {'dia': Horario.JUEVES, 'inicio': time(9, 0), 'fin': time(13, 0)},
            {'dia': Horario.VIERNES, 'inicio': time(9, 0), 'fin': time(13, 0)},
            # Tarde
            {'dia': Horario.LUNES, 'inicio': time(14, 0), 'fin': time(18, 0)},
            {'dia': Horario.MARTES, 'inicio': time(14, 0), 'fin': time(18, 0)},
            {'dia': Horario.MIERCOLES, 'inicio': time(14, 0), 'fin': time(18, 0)},
            {'dia': Horario.JUEVES, 'inicio': time(14, 0), 'fin': time(18, 0)},
            {'dia': Horario.VIERNES, 'inicio': time(14, 0), 'fin': time(18, 0)},
        ]

        # 3. Iterar sobre cada profesional y asignarle el horario
        total_creados = 0
        for prof in profesionales:
            self.stdout.write(f'Procesando horarios para {prof.get_full_name()}...')
            for slot in horario_estandar:
                # get_or_create evita duplicados. Si ya existe un horario para ese profesional
                # en ese día y hora, no lo creará de nuevo.
                horario, created = Horario.objects.get_or_create(
                    profesional=prof,
                    dia=slot['dia'],
                    hora_inicio=slot['inicio'],
                    defaults={'hora_fin': slot['fin']}
                )
                if created:
                    total_creados += 1
                    self.stdout.write(f'  -> Creado horario: {horario.get_dia_display()} de {horario.hora_inicio.strftime("%H:%M")} a {horario.hora_fin.strftime("%H:%M")}')

        self.stdout.write(self.style.SUCCESS(f'\n--- Poblado de horarios finalizado. Se crearon {total_creados} nuevos horarios. ---'))
