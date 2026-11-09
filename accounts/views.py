from django.contrib.auth.views import LoginView, LogoutView


class SalesLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True


class SalesLogoutView(LogoutView):
    next_page = "login"
