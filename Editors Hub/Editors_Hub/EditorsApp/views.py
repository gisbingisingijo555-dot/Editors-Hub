# Create your views here.

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import EditRequest, EditorProfile, Message, UserProfile, Work, Rating 
from .forms import UserRegisterForm, EditorProfileForm, UserUpdateForm, UserProfileUpdateForm, WorkForm, SupportForm
from django.contrib.auth import authenticate, login
from django.contrib import messages
from datetime import timedelta
from django.http import JsonResponse
from django.db.models import Q, Avg, Count, F, FloatField, ExpressionWrapper
from django.utils import timezone
import random
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string


def home(request):
    is_editor = False
    is_pending = False
    is_rejected = False
    unread_count = 0

    if request.user.is_authenticated:

        unread_count = Message.objects.filter(
            receiver=request.user,
            is_read=False
        ).count()

        if hasattr(request.user, 'editorprofile'):
            status = request.user.editorprofile.status

            if status == 'approved':
                is_editor = True
            elif status == 'pending':
                is_pending = True
            elif status == 'rejected':
                is_rejected = True

    return render(request, 'home.html', {
        'is_editor': is_editor,
        'is_pending': is_pending,
        'is_rejected': is_rejected,
        'unread_count': unread_count,
    })


#  EDITORS 
@login_required
def editors_list(request):
    query = request.GET.get('search')

    editors = EditorProfile.objects.filter(status='approved').exclude(mode='offline')

    if query:
        editors = editors.filter(category__name__icontains=query)

    return render(request, 'editors_list.html', {'editors': editors})




@login_required
def editor_profile(request, id):
    editor = get_object_or_404(EditorProfile, id=id)

    has_active_request = False

    if request.user.is_authenticated:
        has_active_request = EditRequest.objects.filter(
            user=request.user,
            editor=editor.user,
            status__in=['pending', 'accepted', 'finished']
        ).exists()

    return render(request, 'editor_profile.html', {
        'editor': editor,
        'has_active_request': has_active_request
    })



@login_required
def send_message(request, user_id):
    if request.method == "POST":
        receiver = get_object_or_404(User, id=user_id)
        content = request.POST.get("content")

        if content:
            Message.objects.create(
                sender=request.user,
                receiver=receiver,
                content=content
            )
            return JsonResponse({"status": "success"})

    return JsonResponse({"status": "error"})
 


@login_required
def inbox(request):
    # Get all related messages
    all_messages = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    )

    user_ids = set()

    for msg in all_messages:
        if msg.sender != request.user:
            user_ids.add(msg.sender.id)
        if msg.receiver != request.user:
            user_ids.add(msg.receiver.id)

    users = User.objects.filter(id__in=user_ids)

    # Sidebar data
    user_data = []

    for u in users:
        last_msg = Message.objects.filter(
            Q(sender=request.user, receiver=u) |
            Q(sender=u, receiver=request.user)
        ).order_by('-timestamp').first()

        unread_count = Message.objects.filter(
            sender=u,
            receiver=request.user,
            is_read=False
        ).count()

        if last_msg:
            if last_msg.is_unsent:
                preview = "Message unsent"
            else:
                preview = last_msg.content
        else:
                preview = ""

        user_data.append({
            'user': u,
            'last_msg': preview,
            'unread': unread_count
        })

    selected_user_id = request.GET.get('user')
    selected_user = None
    chat_messages = []

    if selected_user_id:
        selected_user = get_object_or_404(User, id=selected_user_id)

        chat_messages = Message.objects.filter(
            Q(sender=request.user, receiver=selected_user) |
            Q(sender=selected_user, receiver=request.user)
        ).order_by('timestamp')

        # Mark as read
        Message.objects.filter(
            sender=selected_user,
            receiver=request.user,
            is_read=False
        ).update(is_read=True)

    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    return render(request, 'inbox.html', {
        'user_data': user_data,
        'messages': chat_messages,
        'selected_user': selected_user,
        'today': today,
        'yesterday': yesterday,
    })



def signup(request):

    if request.user.is_authenticated:
        return redirect('home')

    # 🚫 BLOCK MULTIPLE SUBMITS
    if request.session.get('otp_sending'):
        messages.warning(request, "OTP is already being sent.")
        return redirect('signup')

    if request.method == 'POST':

        form = UserRegisterForm(request.POST)

        if form.is_valid():

            # 🔒 LOCK
            request.session['otp_sending'] = True

            try:

                # ⏳ RATE LIMIT
                otp_time = request.session.get('otp_time')

                if otp_time:

                    otp_time = timezone.datetime.fromisoformat(otp_time)

                    if timezone.now() < otp_time + timedelta(seconds=60):

                        messages.warning(
                            request,
                            "Please wait before requesting another OTP."
                        )

                        request.session['otp_sending'] = False

                        return redirect('verify_signup_otp')

                # GENERATE OTP
                otp = generate_otp()

                # SAVE SESSION
                request.session['signup_data'] = request.POST.dict()

                request.session['signup_otp'] = otp

                request.session['signup_otp_time'] = str(timezone.now())

                # =========================
                # HTML EMAIL TEMPLATE
                # =========================

                html_content = render_to_string(

                    'emails/otp_email.html',

                    {
                        'username': form.cleaned_data['username'],
                        'otp': otp,
                    }
                )

                # =========================
                # EMAIL
                # =========================

                email = EmailMultiAlternatives(

                    subject='Editors Hub OTP Verification',

                    body=f'Your OTP is {otp}',

                    from_email=settings.EMAIL_HOST_USER,

                    to=[form.cleaned_data['email']]
                )

                # ATTACH HTML
                email.attach_alternative(
                    html_content,
                    "text/html"
                )

                # SEND
                email.send()

                messages.success(
                    request,
                    "OTP sent successfully."
                )

                # 🔓 UNLOCK
                request.session['otp_sending'] = False

                return redirect('verify_signup_otp')

            except Exception as e:

                print(e)

                request.session['otp_sending'] = False

                messages.error(
                    request,
                    "Failed to send OTP."
                )

                return redirect('signup')

        else:

            messages.error(
                request,
                "Please correct the errors below."
            )

    else:

        form = UserRegisterForm()

    return render(request, 'register.html', {
        'form': form
    })



@login_required
def create_editor_profile(request):

    profile = EditorProfile.objects.filter(user=request.user).first()

    if request.method == "POST":

        if not profile:
            profile = EditorProfile(user=request.user)

        form = EditorProfileForm(request.POST, request.FILES, instance=profile)

        files = request.FILES.getlist('works')

        if form.is_valid():
            editor = form.save(commit=False)

            if 'profile_image' in request.FILES:
                editor.profile_image = request.FILES['profile_image']

            editor.user = request.user

            # 🔥 FIX THIS LINE
            editor.status = 'pending'

            editor.save()
            form.save_m2m()

            if files:
                for file in files:
                    Work.objects.create(
                        editor=editor,
                        media=file
                    )

            messages.success(
                request,
                "Your editor profile has been submitted and is waiting for admin approval."
            )

            return redirect('home')

        else:
            messages.error(request, "Something went wrong.")

    else:
        form = EditorProfileForm(instance=profile)

    return render(request, 'create_profile.html', {'form': form})


def custom_login(request):
    if request.method == 'POST':
        username_input = request.POST.get('username').strip()
        password = request.POST.get('password')

        user = authenticate(request, username=username_input, password=password)

        if user is None:
            try:
                user_obj = User.objects.get(email__iexact=username_input)
                user = authenticate(
                    request,
                    username=user_obj.username,
                    password=password
                )
            except User.DoesNotExist:
                pass

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Invalid email / username or password")
            return redirect('login')

    return render(request, 'login.html')



@login_required
def get_messages(request, user_id):
    other_user = get_object_or_404(User, id=user_id)

    messages = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).order_by('timestamp')

    data = []

    for msg in messages:
        data.append({
            'id': msg.id,
            'sender': msg.sender.username,
            'content': (
                "You unsent a message"
                if msg.is_unsent and msg.sender == request.user
                else
                f"{msg.sender.username} unsent a message"
                if msg.is_unsent
                else
                msg.content
            ),
            'time': msg.timestamp.strftime("%I:%M %p"),
            'full_time': msg.timestamp.isoformat(),
            'is_me': msg.sender == request.user,
            'is_unsent': msg.is_unsent,
        })

    return JsonResponse({'messages': data})


@login_required
def get_sidebar(request):
    messages = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    )

    user_ids = set()

    for msg in messages:
        if msg.sender != request.user:
            user_ids.add(msg.sender.id)
        if msg.receiver != request.user:
            user_ids.add(msg.receiver.id)

    users = User.objects.filter(id__in=user_ids)

    data = []

    for u in users:
        last_msg = Message.objects.filter(
            Q(sender=request.user, receiver=u) |
            Q(sender=u, receiver=request.user)
        ).order_by('-timestamp').first()

        unread = Message.objects.filter(
            sender=u,
            receiver=request.user,
            is_read=False
        ).count()

        profile_pic = "/media/default.jpg"

        if hasattr(u, 'editorprofile') and u.editorprofile.profile_image:
            profile_pic = u.editorprofile.profile_image.url
        elif hasattr(u, 'userprofile') and u.userprofile.profile_pic:
            profile_pic = u.userprofile.profile_pic.url

        data.append({
            "id": u.id,
            "username": u.username,
            "last_msg": (
                "This message was unsent"
            if last_msg and last_msg.is_unsent
            else last_msg.content if last_msg else ""
        ),
        "unread": unread,
        "profile_pic": profile_pic,
    })

    return JsonResponse({"users": data})

@login_required
def unread_count(request):
    count = Message.objects.filter(
        receiver=request.user,
        is_read=False
    ).count()

    return JsonResponse({"count": count})



@login_required
def user_profile(request):

    user = request.user

    print("EDITOR EXISTS:", hasattr(user, 'editorprofile'))

    if hasattr(user, 'editorprofile'):
        print("EDITOR STATUS:", user.editorprofile.status)
    is_editor = hasattr(user, 'editorprofile')

    # =========================
    # USER HAS EDITOR PROFILE
    # =========================
    if is_editor:

        editor = user.editorprofile

        # =========================
        # APPROVED EDITOR
        # =========================
        if editor.status.lower() == 'approved':

            works = editor.works.all().order_by('-uploaded_at')

            if request.method == 'POST':

                original_email = request.user.email.strip().lower()   # ✅ FIX

                u_form = UserUpdateForm(request.POST, instance=user)
                e_form = EditorProfileForm(request.POST, request.FILES, instance=editor)

                if u_form.is_valid() and e_form.is_valid():

                    new_email = u_form.cleaned_data.get('email').strip().lower()

                    # ✅ NOW THIS WORKS CORRECTLY
                    if new_email != original_email:

                        otp = generate_otp()

                        request.session['profile_update_otp'] = otp
                        request.session['profile_update_otp_time'] = timezone.now().isoformat()

                        request.session['profile_update_data'] = {
                            'username': u_form.cleaned_data['username'],
                            'email': new_email,
                # other fields...
                        }

                        send_otp_email(
                            new_email,
                            request.user.username,
                            otp,
                            "Confirm Profile Update"
                        )

                        return redirect('verify_update_otp')

                    # ✅ SAVE DIRECTLY
                    u_form.save()
                    e_form.save()

                    return redirect('user_profile')
                    
                else:
                    print("FORM VALIDATION FAILED")
                    print(u_form.errors)
                    print(e_form.errors)


                # WORK UPLOAD
            if request.FILES.get('media') and w_form.is_valid():
                    work = w_form.save(commit=False)
                    work.editor = editor
                    work.save()

                    messages.success(request, "Work uploaded successfully")
                    return redirect('user_profile')

            else:
                u_form = UserUpdateForm(instance=user)
                e_form = EditorProfileForm(instance=editor)
                w_form = WorkForm()

            return render(request, 'profile.html', {
                'u_form': u_form,
                'e_form': e_form,
                'w_form': w_form,
                'editor': editor,
                'works': works,
                'is_editor': True,
            })

        # =========================
        # PENDING / REJECTED EDITOR
        # =========================
        else:

            profile = user.userprofile

            if request.method == 'POST':

                u_form = UserUpdateForm(request.POST, instance=user)
                p_form = UserProfileUpdateForm(request.POST, request.FILES, instance=profile)

                print("USER VALID =", u_form.is_valid())
                print("PROFILE VALID =", p_form.is_valid())

                print("USER ERRORS =", u_form.errors)
                print("PROFILE ERRORS =", p_form.errors)

                if u_form.is_valid() and p_form.is_valid():

                    new_email = u_form.cleaned_data.get('email').strip().lower()
                    current_email = User.objects.get(
                        pk=request.user.pk
                        ).email.strip().lower()

                    print("CURRENT EMAIL =", current_email)
                    print("NEW EMAIL =", new_email)
                    print("EMAIL CHANGED =", new_email != current_email)

                    if new_email != current_email:

                        print("GENERATING OTP")

                        otp = generate_otp()

                        request.session['profile_update_otp'] = otp
                        request.session['profile_update_otp_time'] = timezone.now().isoformat()

                        request.session['profile_update_data'] = {
                            'username': u_form.cleaned_data.get('username'),
                            'email': new_email,
                            'phone': p_form.cleaned_data.get('phone'),
                        }

                        try:

                            print("SENDING OTP TO =", new_email)

                            send_otp_email(
                                new_email,
                                request.user.username,
                                otp,
                                "Confirm Profile Update"
                            )

                            print("EMAIL SEND")

                            messages.success(request, "OTP sent to your new email.")
                            return redirect('verify_update_otp')

                        except Exception as e:
                            print("EMAIL ERROR =",e)
                            messages.error(request, "Failed to send OTP.")
                            return redirect('user_profile')

                    u_form.save()
                    p_form.save()

                    messages.success(request, "Profile updated successfully")
                    return redirect('user_profile')

            else:
                u_form = UserUpdateForm(instance=user)
                p_form = UserProfileUpdateForm(instance=profile)

            return render(request, 'profile.html', {
                'u_form': u_form,
                'p_form': p_form,
                'editor': editor,
                'is_editor': True,
            })

    # =========================
    # NORMAL USER
    else:

        print("NORMAL USER BRANCH")

        profile = user.userprofile

        if request.method == 'POST':

            print("POST DATA =", request.POST)

            print("NORMAL USER POST RECEIVED")

            u_form = UserUpdateForm(request.POST, instance=user)
            p_form = UserProfileUpdateForm(request.POST, request.FILES, instance=profile)

            print("USER VALID =", u_form.is_valid())
            print("PROFILE VALID =", p_form.is_valid())

            print("USER ERRORS =", u_form.errors)
            print("PROFILE ERRORS =", p_form.errors)

            if u_form.is_valid() and p_form.is_valid():

                print("REQUEST USER EMAIL =", request.user.email)

                print("USER INSTANCE EMAIL =", user.email)

                print("FORM EMAIL =", u_form.cleaned_data.get('email'))

                print("DB EMAIL =", User.objects.get(pk=user.pk).email)

                new_email = u_form.cleaned_data.get('email').strip().lower()

                current_email = User.objects.get(
                    pk=request.user.pk
                    ).email.strip().lower()

                print("CURRENT EMAIL =", current_email)
                print("NEW EMAIL =", new_email)
                print("EMAIL CHANGED =", new_email != current_email)

                if new_email != current_email:

                    print("GENERATING OTP")

                    otp = generate_otp()

                    request.session['profile_update_otp'] = otp
                    request.session['profile_update_otp_time'] = timezone.now().isoformat()

                    request.session['profile_update_data'] = {
                        'username': u_form.cleaned_data.get('username'),
                        'email': new_email,
                        'phone': p_form.cleaned_data.get('phone'),
                    }

                    try:

                        print("SENDING OTP TO =", new_email)

                        send_mail(
                            'Profile Update Verification',
                            f'Your OTP is {otp}',
                            settings.EMAIL_HOST_USER,
                            [new_email],
                            fail_silently=False,
                        )

                        print("EMAIL SENT")

                        messages.success(request, "OTP sent to your new email.")
                        return redirect('verify_update_otp')

                    except Exception as e:
                        print("EMAIL ERROR =", e)
                        messages.error(request, "Failed to send OTP.")
                        return redirect('user_profile')

                u_form.save()
                p_form.save()

                messages.success(request, "Profile updated successfully")
                return redirect('user_profile')

        else:
            u_form = UserUpdateForm(instance=user)
            p_form = UserProfileUpdateForm(instance=profile)

        return render(request, 'profile.html', {
            'u_form': u_form,
            'p_form': p_form,
            'is_editor': False,
        })


    

@login_required
def delete_work(request, work_id):
    work = get_object_or_404(Work, id=work_id, editor__user=request.user)

    if request.method == "POST":
        work.delete()
        messages.success(request, "Work deleted successfully")
    
    return redirect('user_profile')


@login_required
def rate_editor(request, editor_id):
    editor = get_object_or_404(EditorProfile, id=editor_id)

    if request.method == "POST":
        value = request.POST.get("rating")
        comment = request.POST.get("comment")

        if not value:
            messages.error(request, "Please select a rating")
            return redirect('editor_profile', id=editor.id)

        try:
            value = int(value)
        except ValueError:
            messages.error(request, "Invalid rating")
            return redirect('editor_profile', id=editor.id)

        if value < 1 or value > 5:
            messages.error(request, "Rating must be between 1 and 5")
            return redirect('editor_profile', id=editor.id)

        Rating.objects.update_or_create(
            user=request.user,
            editor=editor,
            defaults={
                'rating': value,
                'comment': comment
            }
        )

        messages.success(request, "Review submitted successfully!")
        return redirect('editor_profile', id=editor.id)
    

@login_required
def top_editors(request):

    editors = EditorProfile.objects.filter(status='approved').annotate(
    avg_rating=Avg('ratings__rating'),
    review_count=Count('ratings'),   # 🔥 CHANGE NAME
    ).annotate(
        score=ExpressionWrapper(
            F('avg_rating') * F('review_count'),
            output_field=FloatField()
        )
    ).order_by('-score')

    return render(request, 'top_editors.html', {
        'editors': editors
    })


def generate_otp():
    return str(random.randint(100000, 999999))


@login_required
def verify_otp(request):
    profile = request.user.userprofile

    if request.method == "POST":
        entered_otp = request.POST.get('otp')

        # ✅ Expiry check
        if profile.otp_created_at:
            if timezone.now() > profile.otp_created_at + timedelta(minutes=5):
                messages.error(request, "OTP expired. Please request a new one.")
                return redirect('send_otp')

        if entered_otp == profile.email_otp:
            profile.is_email_verified = True
            profile.email_otp = None
            profile.otp_created_at = None
            profile.save()

            messages.success(request, "Email verified successfully!")
            return redirect('create_profile')

        else:
            messages.error(request, "Invalid OTP")

    return render(request, 'verify_otp.html')


@login_required
def send_otp(request):
    profile = request.user.userprofile

    # ✅ Already verified
    if profile.is_email_verified:
        return redirect('create_profile')

    # ✅ Rate limit (1 min)
    if profile.otp_created_at and timezone.now() < profile.otp_created_at + timedelta(seconds=60):
        messages.warning(request, "Please wait before requesting another OTP.")
        return redirect('verify_otp')

    otp = generate_otp()
    profile.email_otp = otp
    profile.otp_created_at = timezone.now()
    profile.is_email_verified = False
    profile.save()

    try:
        send_otp_email(
            request.user.email,
            request.user.username,
            otp,
            "Email Verification"
       )
        
    except Exception:
        messages.error(request, "Failed to send OTP. Try again later.")
        return redirect('home')

    messages.success(request, "OTP sent to your email.")
    return redirect('verify_otp')



def verify_signup_otp(request):

    if request.method == "POST":

        entered_otp = request.POST.get('otp')
        session_otp = request.session.get('signup_otp')
        otp_time = request.session.get('signup_otp_time')

        if not session_otp:
            messages.error(request, "Session expired. Please signup again.")
            return redirect('signup')

        # EXPIRY CHECK
        if otp_time:
            otp_time = timezone.datetime.fromisoformat(otp_time)
            if timezone.now() > otp_time + timedelta(minutes=5):
                messages.error(request, "OTP expired")
                return redirect('signup')

        if entered_otp == session_otp:

            data = request.session.get('signup_data')
            form = UserRegisterForm(data)

            if form.is_valid():
                user = form.save()

                profile, _ = UserProfile.objects.get_or_create(user=user)
                profile.phone = form.cleaned_data['phone']
                profile.gender = form.cleaned_data['gender']
                profile.age = form.cleaned_data['age']
                profile.is_email_verified = True
                profile.save()

                request.session.flush()

                messages.success(request, "Account created successfully!")
                return redirect('login')

            messages.error(request, "Invalid form data. Try again.")
            return redirect('signup')

        messages.error(request, "Invalid OTP")
        return redirect('verify_signup_otp')

    return render(request, 'verify_otp.html')


@login_required
def verify_update_otp(request):

    if request.method == 'POST':

        entered_otp = request.POST.get('otp')

        session_otp = request.session.get('profile_update_otp')
        otp_time = request.session.get('profile_update_otp_time')
        data = request.session.get('profile_update_data')

        if not session_otp or not data:
            messages.error(request, "Session expired. Try again.")
            return redirect('user_profile')

        # EXPIRY CHECK
        if otp_time:
            otp_time = timezone.datetime.fromisoformat(otp_time)
            if timezone.now() > otp_time + timedelta(minutes=5):
                messages.error(request, "OTP expired")
                return redirect('user_profile')

        if entered_otp == session_otp:

            user = request.user
            profile = user.userprofile

            user.username = data['username']
            user.email = data['email']
            user.save()

            profile.phone = data.get('phone', profile.phone)
            profile.save()

            # editor update (safe check)
            if hasattr(user, 'editorprofile') and 'name' in data:

                editor = user.editorprofile

                editor.name = data['name']
                editor.age = data['age']
                editor.gender = data['gender']
                editor.phone = data['phone']
                editor.price = data['price']
                editor.bio = data['bio']
                editor.experience_years = data['experience_years']
                editor.softwares = data['softwares']
                editor.address = data['address']
                editor.portfolio = data['portfolio']

                editor.save()

                categories = request.session.get(
                    'profile_update_categories',
                []
                )

                languages = request.session.get(
                    'profile_update_languages',
                []
                )

                editor.category.set(categories)
                editor.language.set(languages)

            # CLEAR SESSION
            request.session.pop('profile_update_otp', None)
            request.session.pop('profile_update_otp_time', None)
            request.session.pop('profile_update_data', None)

            messages.success(request, "Profile updated successfully!")
            return redirect('user_profile')

        messages.error(request, "Invalid OTP")
        return redirect('verify_update_otp')

    return render(request, 'verify_otp.html')


@login_required
def change_availability(request):
    if request.method == "POST":
        mode = request.POST.get("mode")

        profile = request.user.editorprofile

        if mode in ['active', 'busy', 'offline']:
            profile.mode = mode   
            profile.save()

    return redirect('user_profile')


def terms_page(request):
    return render(request, 'terms.html')



def privacy(request):
    return render(request, 'privacy.html')


@login_required
def contact_support(request):

    if request.method == "POST":

        form = SupportForm(request.POST)

        if form.is_valid():

            support = form.save(commit=False)

            support.user = request.user

            support.save()

            # GENERATE TICKET ID
            ticket_id = random.randint(100000, 999999)

            # HTML EMAIL
            html_content = render_to_string(
                'emails/support_email.html',
                {
                    'user': request.user,
                    'support': support,
                    'ticket_id': ticket_id,
                }
            )

            # EMAIL
            email = EmailMultiAlternatives(

                subject=f"[Ticket #{ticket_id}] {support.subject}",

                body=support.message,

                from_email='editors.hub.page@gmail.com',

                to=['editors.hub.page@gmail.com']
            )

            email.attach_alternative(
                html_content,
                "text/html"
            )

            email.send()

            messages.success(
                request,
                "Support request sent successfully."
            )

            return redirect('contact_support')

    else:

        form = SupportForm()

    return render(request, 'contact_support.html', {
        'form': form
    })


def send_otp_email(email_address, username, otp, title):

    if "Profile" in title:
        message = "Use this OTP to confirm your profile update."
    elif "Verification" in title:
        message = "Use this OTP to verify your account."
    else:
        message = "Use this OTP."

    html_content = render_to_string(
        'emails/otp_email.html',
        {
            'username': username,
            'otp': otp,
            'title': title,
            'message': message,
            'expiry': 5
        }
    )

    email = EmailMultiAlternatives(
        subject=title,
        body=f'Your OTP is {otp}',
        from_email=settings.EMAIL_HOST_USER,
        to=[email_address]
    )

    email.attach_alternative(html_content, "text/html")
    email.send()


@login_required
def unsend_message(request, message_id):

    msg = get_object_or_404(
        Message,
        id=message_id,
        sender=request.user
    )

    msg.is_unsent = True
    msg.save()

    return JsonResponse({
        "success": True
    })


@login_required
def send_edit_request(request, editor_id):

    editor = get_object_or_404(User, id=editor_id)

    if request.method == "POST":

        category_id = request.POST.get('category')
        message = request.POST.get('message')
        file = request.FILES.get('file')

        # ✅ FIX: BLOCK ALL ACTIVE REQUESTS
        existing_request = EditRequest.objects.filter(
            user=request.user,
            editor=editor,
            status__in=['pending', 'accepted', 'finished']
        ).exists()

        if existing_request:
            messages.warning(
                request,
                "You already have an active request with this editor."
            )
            return redirect('editor_profile', id=editor.editorprofile.id)

        # ✅ CREATE NEW REQUEST
        EditRequest.objects.create(
            user=request.user,
            editor=editor,
            category_id=category_id,
            message=message,
            file=file
        )

        messages.success(request, "Request sent successfully!")
        return redirect('editor_profile', id=editor.editorprofile.id)


@login_required
def editor_dashboard(request):

    requests = EditRequest.objects.filter(
        editor=request.user
    ).select_related('user', 'category').order_by('-created_at')

    # ✅ ADD COUNTS
    pending_count = requests.filter(status='pending').count()
    accepted_count = requests.filter(status='accepted').count()
    rejected_count = requests.filter(status='rejected').count()

    return render(request, 'editor_dashboard.html', {
        'requests': requests,
        'pending_count': pending_count,
        'accepted_count': accepted_count,
        'rejected_count': rejected_count,
    })


@login_required
def accept_request(request, request_id):
    if request.method == "POST":
        req = get_object_or_404(EditRequest, id=request_id, editor=request.user)
        req.status = 'accepted'
        req.save()
    return redirect('editor_dashboard')


@login_required
def reject_request(request, request_id):
    if request.method == "POST":
        req = get_object_or_404(EditRequest, id=request_id, editor=request.user)
        req.status = 'rejected'
        req.save()
    return redirect('editor_dashboard')

@login_required
def finish_request(request, request_id):
    if request.method == "POST":
        req = get_object_or_404(EditRequest, id=request_id, editor=request.user)
        req.status = 'finished'
        req.save()
    return redirect('editor_dashboard')


@login_required
def user_dashboard(request):

    requests = EditRequest.objects.filter(
        user=request.user
    ).select_related('editor', 'category').order_by('-created_at')

    return render(request, 'user_dashboard.html', {
        'requests': requests,
        'pending_count': requests.filter(status='pending').count(),
        'accepted_count': requests.filter(status='accepted').count(),
        'rejected_count': requests.filter(status='rejected').count(),
        'finished_count': requests.filter(status='finished').count(),
    })



@login_required
def finish_request(request, request_id):
    req = get_object_or_404(EditRequest, id=request_id, editor=request.user)

    if request.method == "POST":
        req.drive_link = request.POST.get('drive_link')
        req.amount = request.POST.get('amount')
        req.status = 'finished'
        req.save()

        return redirect('editor_dashboard')

    return render(request, 'finish_form.html', {'req': req})


@login_required
def make_payment(request, request_id):
    req = get_object_or_404(EditRequest, id=request_id, user=request.user)

    if request.method == "POST":
        req.status = 'paid'
        req.save()

    return redirect('user_dashboard')