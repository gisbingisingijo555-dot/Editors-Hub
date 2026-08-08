from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Message, EditorProfile, UserProfile, Work, Category, SupportMessage, Language


# ================= SIGNUP FORM =================
class UserRegisterForm(UserCreationForm):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Name'})
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Username'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Email'})
    )
    phone = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Phone Number'})
    )

    gender = forms.ChoiceField(
        choices=[('', 'Select Gender'), ('M', 'Male'), ('F', 'Female'), ('O', 'Other')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    age = forms.IntegerField(
        widget=forms.NumberInput(attrs={'placeholder': 'Age'})
    )

    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'})
    )

    class Meta:
        model = User
        fields = [
            'name', 'username', 'email', 'phone',
            'gender', 'age', 'password1', 'password2'
        ]

    # ================= VALIDATIONS =================

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')

        if not phone.isdigit() or len(phone) != 10 or phone[0] not in ['6', '7', '8', '9']:
            raise forms.ValidationError("Enter a valid 10-digit phone number")

        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email already exists")

        return email

    def clean_age(self):
        age = self.cleaned_data.get('age')

        if age < 10 or age > 100:
            raise forms.ValidationError("Enter a valid age")

        return age

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")

        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match")

        return cleaned_data

    # ================= SAVE USER =================
    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['name']
        user.email = self.cleaned_data['email']

        if commit:
            user.save()

            # ✅ SAVE EXTRA DATA INTO PROFILE (FIXED)
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.phone = self.cleaned_data.get('phone')
            profile.gender = self.cleaned_data.get('gender')
            profile.age = self.cleaned_data.get('age')
            profile.save()

        return user


# ================= MESSAGE FORM =================
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']


# ================= EDITOR PROFILE =================
class EditorProfileForm(forms.ModelForm):
    category = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

    language = forms.ModelMultipleChoiceField(
        queryset=Language.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

    class Meta:
        model = EditorProfile
        fields = [
            'name', 'age', 'gender', 'email', 'phone', 'price',
            'category', 'profile_image',
            'language', 'bio', 'experience_years',
            'softwares', 'address', 'id_proof', 'portfolio'
        ]


# ================= USER UPDATE =================
class UserUpdateForm(forms.ModelForm):

    def clean_email(self):
        email = self.cleaned_data['email']

        if User.objects.filter(
            email__iexact=email
        ).exclude(pk=self.instance.pk).exists():

            raise forms.ValidationError(
                "Email already exists."
            )

        return email

    class Meta:
        model = User
        fields = ['username', 'email']


# ================= USER PROFILE UPDATE =================
class UserProfileUpdateForm(forms.ModelForm):

    name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your name'
        })
    )

    class Meta:
        model = UserProfile
        fields = ['profile_pic', 'phone', 'gender', 'age']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.user:
            self.fields['name'].initial = self.instance.user.first_name

    def save(self, commit=True):
        profile = super().save(commit=False)

        if profile.user:
            profile.user.first_name = self.cleaned_data.get('name')
            profile.user.save()

        if commit:
            profile.save()

        return profile


# ================= WORK FORM =================
class WorkForm(forms.ModelForm):
    class Meta:
        model = Work
        fields = ['media']


# ================= SUPPORT FORM =================
class SupportForm(forms.ModelForm):

    class Meta:
        model = SupportMessage
        fields = ['subject', 'message']

        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter subject'
            }),

            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Describe your issue...',
                'rows': 6
            })
        }