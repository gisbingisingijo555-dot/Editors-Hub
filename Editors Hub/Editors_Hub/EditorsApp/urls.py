from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import custom_login

urlpatterns = [

    path('', views.home, name='home'),

    path('editors/', views.editors_list, name='editors_list'),
    path('editor/<int:id>/', views.editor_profile, name='editor_profile'),

    path('create-profile/', views.create_editor_profile, name='create_profile'),
    path('signup/', views.signup, name='signup'),

    path('login/', custom_login, name='login'),

    path(
        'logout/',
        auth_views.LogoutView.as_view(next_page='/login/'),
        name='logout'
    ),

    path('message/<int:user_id>/', views.send_message, name='send_message'),
    path('send-message/<int:user_id>/', views.send_message, name='send_message'),
    path(
    'unsend-message/<int:message_id>/',
    views.unsend_message,
    name='unsend_message'
    ),

    path('inbox/', views.inbox, name='inbox'),
    path('get-messages/<int:user_id>/', views.get_messages),
    path('get-sidebar/', views.get_sidebar, name='get_sidebar'),

    path('unread-count/', views.unread_count, name='unread_count'),

    path('change-availability/', views.change_availability, name='change_availability'),

    path('user-profile/', views.user_profile, name='user_profile'),

    path('delete-work/<int:work_id>/', views.delete_work, name='delete_work'),

    path('rate-editor/<int:editor_id>/', views.rate_editor, name='rate_editor'),

    path('top-editors/', views.top_editors, name='top_editors'),

    path('send-otp/', views.send_otp, name='send_otp'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('verify-signup-otp/', views.verify_signup_otp, name='verify_signup_otp'),
    path('verify-update-otp/', views.verify_update_otp, name='verify_update_otp'),

    # CHANGE PASSWORD

    path(
        'change-password/',
        auth_views.PasswordChangeView.as_view(
            template_name='change_password.html',
            success_url='/password-change-done/'
        ),
        name='change_password'
    ),

    path(
        'password-change-done/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='password_change_done.html'
        ),
        name='password_change_done'
    ),

    path('terms/', views.terms_page, name='terms'),
    path('privacy/', views.privacy, name='privacy'),

    path(
    'contact-support/',
    views.contact_support,
    name='contact_support'
    ),


    path('send-request/<int:editor_id>/', views.send_edit_request, name='send_edit_request'),
path('editor-dashboard/', views.editor_dashboard, name='editor_dashboard'),
path('accept-request/<int:request_id>/', views.accept_request, name='accept_request'),
path('reject-request/<int:request_id>/', views.reject_request, name='reject_request'),
path('finish-request/<int:request_id>/', views.finish_request, name='finish_request'),
path('user-dashboard/', views.user_dashboard, name='user_dashboard'),
path('make-payment/<int:request_id>/', views.make_payment, name='make_payment'),

]