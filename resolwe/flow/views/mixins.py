"""Mixins used in Resolwe Viewsets."""
from __future__ import absolute_import, division, print_function, unicode_literals

from django.db import IntegrityError, transaction

from guardian.shortcuts import assign_perm
from guardian.utils import get_anonymous_user
from rest_framework import mixins, status
from rest_framework.decorators import list_route
from rest_framework.response import Response

from resolwe.flow.models import DescriptorSchema
from resolwe.permissions.shortcuts import get_objects_for_user


class ResolweCreateModelMixin(mixins.CreateModelMixin):
    """Mixin to support creating new `Resolwe` models.

    Extends `django_rest_framework`'s class `CreateModelMixin` with:

      * append user's id from request to posted data as `contributor`
        key
      * catch `IntegrityError`s, so we can return HTTP status 409
        instead of raising error

    """

    def create(self, request, *args, **kwargs):
        """Create a resource."""
        ds_slug = request.data.get('descriptor_schema', None)
        if ds_slug:
            ds_query = DescriptorSchema.objects.filter(slug=ds_slug)
            ds_query = get_objects_for_user(request.user, 'view_descriptorschema', ds_query)
            try:
                request.data['descriptor_schema'] = ds_query.latest().pk
            except DescriptorSchema.DoesNotExist:
                return Response(
                    {'descriptor_schema': [
                        'Invalid descriptor_schema slug "{}" - object does not exist.'.format(ds_slug)]},
                    status=status.HTTP_400_BAD_REQUEST)

        if request.user.is_anonymous():
            request.data['contributor'] = get_anonymous_user().pk
        else:
            request.data['contributor'] = request.user.pk

        try:
            return super(ResolweCreateModelMixin, self).create(request, *args, **kwargs)

        except IntegrityError as ex:
            return Response({u'error': str(ex)}, status=status.HTTP_409_CONFLICT)

    def perform_create(self, serializer):
        """Create a resource."""
        with transaction.atomic():
            instance = serializer.save()

            # Assign all permissions to the object contributor.
            for permission in list(zip(*instance._meta.permissions))[0]:  # pylint: disable=protected-access
                assign_perm(permission, instance.contributor, instance)


class ResolweUpdateModelMixin(mixins.UpdateModelMixin):
    """Mixin to support updating `Resolwe` models.

    Extends `django_rest_framework`'s class `UpdateModelMixin` with:

      * translate `descriptor_schema` field from DescriptorSchema's
        slug to its id and return 400 error Response if it doesn't
        exists

    """

    def update(self, request, *args, **kwargs):
        """Update a resource."""
        ds_slug = request.data.get('descriptor_schema', None)
        if ds_slug:
            ds_query = DescriptorSchema.objects.filter(slug=ds_slug)
            ds_query = get_objects_for_user(request.user, 'view_descriptorschema', ds_query)
            try:
                request.data['descriptor_schema'] = ds_query.latest().pk
            except DescriptorSchema.DoesNotExist:
                return Response(
                    {'descriptor_schema': [
                        'Invalid descriptor_schema slug "{}" - object does not exist.'.format(ds_slug)]},
                    status=status.HTTP_400_BAD_REQUEST)

        return super(ResolweUpdateModelMixin, self).update(request, *args, **kwargs)


class ResolweCheckSlugMixin(object):
    """Slug validation."""

    @list_route(methods=[u'get'])
    def slug_exists(self, request):
        """Check if given url slug exists.

        Check if slug given in query parameter ``name`` exists. Return
        ``True`` if slug already exists and ``False`` otherwise.

        """
        if not request.user.is_authenticated():
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        if 'name' not in request.query_params:
            return Response({'error': 'Query parameter `name` must be given.'},
                            status=status.HTTP_400_BAD_REQUEST)

        queryset = self.get_queryset()
        slug_name = request.query_params['name']
        return Response(queryset.filter(slug__iexact=slug_name).exists())
