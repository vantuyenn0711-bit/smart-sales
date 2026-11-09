from django.urls import path

from analytics import views

app_name = "analytics"
urlpatterns = [path("", views.reports, name="reports"), path("export/", views.export, name="export")]
