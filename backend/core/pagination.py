"""One pagination helper for the admin APIs: ?page=N&page_size=M."""

from django.core.paginator import EmptyPage, Paginator


def paginate(request, queryset, serialize, default_size=20, max_size=100):
    try:
        size = min(max(int(request.query_params.get("page_size", default_size)), 1), max_size)
        number = max(int(request.query_params.get("page", 1)), 1)
    except (TypeError, ValueError):
        size, number = default_size, 1
    paginator = Paginator(queryset, size)
    try:
        page = paginator.page(number)
    except EmptyPage:
        page = paginator.page(paginator.num_pages or 1) if paginator.count else None
    items = [serialize(obj) for obj in page.object_list] if page else []
    return {
        "count": paginator.count,
        "page": page.number if page else 1,
        "page_size": size,
        "num_pages": paginator.num_pages if paginator.count else 1,
        "results": items,
    }
