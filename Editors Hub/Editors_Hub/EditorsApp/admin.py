from django.contrib import admin
from .models import UserProfile, EditorProfile, Message, Category, Work, Rating, EditRequest


class WorkInline(admin.TabularInline):
    model = Work
    extra = 0
    readonly_fields = ('media', 'uploaded_at', 'preview')

    def preview(self, obj):
        if obj.media:
            return obj.media.url
        return "-"
    preview.short_description = "File URL"


@admin.register(EditorProfile)
class EditorProfileAdmin(admin.ModelAdmin):

    list_display = [
        'user',
        'name',
        'email',
        'phone',
        'status',
    ]

    list_filter = [
        'status',
        'category',
    ]

    search_fields = [
        'user__username',
        'email',
        'phone',
    ]

    filter_horizontal = ('category',)

    inlines = [WorkInline]

    # ✅ FULL ADMIN FORM
    fieldsets = (

    ('Basic Info', {
        'fields': (
            'user',
            'name',
            'email',
            'phone',
            'age',
            'gender',
            'price',
            'profile_image',
            'status',
            'mode',
        )
    }),

    ('Professional Details', {
        'fields': (
            'bio',
            'language',
            'experience_years',
            'softwares',
            'portfolio',
        )
    }),

    ('Address & Verification', {
        'fields': (
            'address',
            'id_proof',
        )
    }),

    ('Categories', {
        'fields': (
            'category',
        )
    }),

    ('Rejection', {
        'fields': (
            'rejection_reason',
        ),
    }),

)

    actions = ['approve_editors', 'reject_editors']

    # ✅ APPROVE
    def approve_editors(self, request, queryset):

        for editor in queryset:
            editor.status = 'approved'
            editor.rejection_reason = None
            editor.save()

    approve_editors.short_description = "Approve selected editors"

    # ❌ REJECT
    def reject_editors(self, request, queryset):

        for editor in queryset:

            if not editor.rejection_reason:
                editor.rejection_reason = "Not specified by admin"

            editor.status = 'rejected'
            editor.save()

    reject_editors.short_description = "Reject selected editors"


from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'get_name',
        'phone',
        'gender',
        'age',
        'is_email_verified',
    )

    search_fields = (
        'user__username',
        'user__email',
        'phone',
    )

    list_filter = (
        'gender',
        'is_email_verified',
    )

    readonly_fields = (
        'get_name',
    )

    fieldsets = (

        ('User Information', {
            'fields': (
                'user',
                'get_name',
                'phone',
                'profile_pic',
            )
        }),

        ('Personal Details', {
            'fields': (
                'gender',
                'age',
            )
        }),

        ('Email Verification', {
            'fields': ( 
                'is_email_verified',
                'email_otp',
                'otp_created_at',
            )
        }),
    )

    def get_name(self, obj):
        return obj.user.first_name

    get_name.short_description = "Name"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):

    list_display = (
        'sender',
        'receiver',
        'timestamp',
        'is_read',
        'is_unsent',
    )

    ordering = ('-timestamp',)

    search_fields = (
        'sender__username',
        'receiver__username',
        'content',
    )


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'editor',
        'rating',
        'created_at',
    )

    list_filter = (
        'rating',
        'created_at',
    )

    search_fields = (
        'user__username',
        'editor__user__username',
        'comment',
    )

    ordering = ('-created_at',)


from .models import EditRequest


@admin.register(EditRequest)
class EditRequestAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'user',
        'editor',
        'category',
        'status',
        'amount',
        'created_at',
    )

    list_filter = (
        'status',
        'category',
        'created_at',
    )

    search_fields = (
        'user__username',
        'editor__username',
        'message',
    )

    ordering = ('-created_at',)

    readonly_fields = (
        'created_at',
    )

    fieldsets = (

        ('Basic Info', {
            'fields': (
                'user',
                'editor',
                'category',
                'message',
            )
        }),

        ('Work Status', {
            'fields': (
                'status',
                'amount',
                'drive_link',
            )
        }),

        ('Timestamps', {
            'fields': (
                'created_at',
            )
        }),

    )

    actions = ['mark_as_paid', 'mark_as_finished']

    # ✅ MARK AS PAID
    def mark_as_paid(self, request, queryset):
        queryset.update(status='paid')
    mark_as_paid.short_description = "Mark selected as Paid"

    # ✅ MARK AS FINISHED
    def mark_as_finished(self, request, queryset):
        queryset.update(status='finished')
    mark_as_finished.short_description = "Mark selected as Finished"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = ('name',)
    search_fields = ('name',)