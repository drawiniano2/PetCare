"""

URL configuration for config project.



The `urlpatterns` list routes URLs to views. For more information please see:

    https://docs.djangoproject.com/en/6.1/topics/http/urls/

Examples:

Function views

    1. Add an import:  from my_app import views

    2. Add a URL to urlpatterns:  path('', views.home, name='home')

Class-based views

    1. Add an import:  from other_app.views import Home

    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')

Including another URLconf

    1. Import the include() function: from django.urls import include, path

    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))

"""

from django.contrib import admin
from django.contrib.auth import views as auth_views

from django.urls import include, path

from config.views import dashboard, panel_personal



urlpatterns = [
    path("recordatorios/", include("recordatorios.urls")),

    path("personal/", panel_personal, name="panel_personal"),

    path(
        "accounts/login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="petcare_login",
    ),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(
        ),
        name="petcare_logout",
    ),


    path("accounts/", include("accounts.urls")),
    path("historial-clinico/", include("historial_clinico.urls")),

    path("citas/", include("citas.urls")),

    path("horarios/", include("horarios.urls")),

    path('', dashboard, name='dashboard'),

    path('admin/', admin.site.urls),

    path('tutores/', include('tutores.urls')),

    path('mascotas/', include('mascotas.urls')),

    path('veterinarios/', include('veterinarios.urls')),

]







