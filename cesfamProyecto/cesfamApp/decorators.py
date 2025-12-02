from functools import wraps
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.contrib import messages
from .models import CustomUser

def role_required(allowed_roles):
    """
    Decorador que comprueba si un usuario pertenece a uno de los roles permitidos y permite mostrar mensajes correctamente.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                messages.error(request, 'Debes iniciar sesión para ver esta página.')
                return redirect('login_page')
            if user.rol not in allowed_roles:
                messages.error(request, 'No tienes los permisos necesarios para acceder a esta página.')
                return redirect('login_page')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# Decoradores específicos por rol
admin_required = role_required([CustomUser.ROL_PROFESIONAL, CustomUser.ROL_ADMIN])
profesional_required = role_required([CustomUser.ROL_PROFESIONAL, CustomUser.ROL_ADMIN])
paciente_required = role_required([CustomUser.ROL_PACIENTE])