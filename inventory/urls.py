from django.urls import path

from inventory.views import movement_list

app_name = "inventory"
urlpatterns = [path("", movement_list, name="movement_list")]
