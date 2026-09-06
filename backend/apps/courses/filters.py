import django_filters

from .models import Course


class CourseFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category__slug")
    level = django_filters.CharFilter(field_name="level")
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = Course
        fields = ("category", "level", "min_price", "max_price")

    def filter_search(self, queryset, name, value):
        return queryset.filter(title__icontains=value)
