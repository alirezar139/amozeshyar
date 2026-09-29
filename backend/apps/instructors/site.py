from .models import InstructorProfile


def get_site_owner() -> InstructorProfile | None:
    """The one instructor this install belongs to (created by `setup_site`)."""
    return InstructorProfile.objects.select_related("user").filter(is_site_owner=True).first()
