import re
import json

from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.contrib.gis.db.models.functions import Centroid, AsGeoJSON

from rest_framework.decorators import api_view
from rest_framework.response import Response

from buildings.models import BuildingFloorSpace

from geojson import Feature

def view_map(request, *args, **kwargs):
    context = {}
    if request.method == 'GET':
        map_name = kwargs.pop('map_name', None)
        building_id, = request.GET.get('buildingid', 1),
        space_id, = request.GET.get('spaceid', 0),
        zoom_level, = request.GET.get('zlevel', 18),
        route_from, = request.GET.get('route_from', ''),
        route_to, = request.GET.get('route_to', ''),
        centerx, = request.GET.get('centerx', 0),
        centery, = request.GET.get('centery', 0),
        floor_num, = request.GET.get('floor', 0),

        context.update({
            'map_name': map_name,
            'building_id': building_id,
            'space_id': int(space_id),
            'zoom_level': zoom_level,
            'route_from': route_from,
            'route_to': route_to,
            'centerx':  float(centerx),
            'centery': float(centery),
            'floor_num': int(floor_num)
        })

    return render(request, context=context, template_name='map.html')



@api_view(['GET'])
def get_room_center(request, big_pk):

    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[-1].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


    ip_addr = get_client_ip(request)
    # print('this is my IP : ' + ip_addr)

    if ip_addr.startswith('127.0.'):
        # if q.keys().index('searchString') < 0:
        #     raise Exception("Couldn't find AKS in parameter q")

        # searchString = q['searchString'].upper()
        searchString = big_pk.upper()

        if re.match('(\d{3}_\d{2}_[A-Z]{1}[A-Z0-9]{1}[0-9]{2}_\d{6})', searchString):
            re_is_match = "yes"
        else:
            raise Exception("input search string does not match AKS form zb 001_10_OG05_111200 or 001_10_U101_111900 ")

        # dont allow empty searchString, too short searchString or too long searchString (50 characters is way too much
        #  and probably a sql attack so we prevent it here aswell
        if searchString == "" or len(searchString) < 10 or len(searchString) > 20:
            raise Exception("searchString is too short. Must be at least 2 characters")

        # check for possible sql attacks etc...
        if '}' in searchString or '{' in searchString or ';' in searchString:
            raise Exception("illegal characters in searchString")

        space_qs = BuildingFloorSpace.objects.filter(room_external_id=big_pk)


        if space_qs:
            att = space_qs.values()[0]

            if att['multi_poly']:
                att['multi_poly'] = None

            centroid_res = BuildingFloorSpace.objects.annotate(json=AsGeoJSON(Centroid('multi_poly'))).get(
                room_external_id=big_pk).json

            res = Feature(geometry=json.loads(centroid_res), properties=att)

            return Response(res)
        else:
            return Response({'error': 'Sorry we did not find any record in our database matching your id = ' + str(big_pk) })
    else:
        # raise Exception("wrong IP! your ip is : " + ip_addr)
        # return HttpResponseForbidden()
        raise PermissionDenied


# # search for strings and return a list of strings and coordinates
# @api_view(['GET'])
# def get_room_center8(request, big_pk):
#     """
#     parameter q: is jsonrpc data format
#     request jsonrpc data
#         {"method":"getRoomCenter",
#         "id":"labla",
#         "params":[{"searchString":"001_20_EG01_018700"}],
#             "jsonrpc":"2.0"}
#
#     returns GEOJSON of room center with attributes AKS, floor, building
#     """
#
#     def get_client_ip(request):
#         x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
#         if x_forwarded_for:
#             ip = x_forwarded_for.split(',')[-1].strip()
#         else:
#             ip = request.META.get('REMOTE_ADDR')
#         return ip
#
#
#     ip_addr = get_client_ip(request)
#     print('this is my IP : ' + ip_addr)
#
#     #if ip_addr.startswith('137.208.'):
#     if ip_addr.startswith('127.0.'):
#         # if q.keys().index('searchString') < 0:
#         #     raise Exception("Couldn't find AKS in parameter q")
#
#         # searchString = q['searchString'].upper()
#         searchString = big_pk.upper()
#
#         if re.match('(\d{3}_\d{2}_[A-Z]{1}[A-Z0-9]{1}[0-9]{2}_\d{6})', searchString):
#             re_is_match = "yes"
#         else:
#             raise Exception("input search string does not match AKS form zb 001_10_OG05_111200 or 001_10_U101_111900 ")
#
#         # dont allow empty searchString, too short searchString or too long searchString (50 characters is way too much
#         #  and probably a sql attack so we prevent it here aswell
#         if searchString == "" or len(searchString) < 10 or len(searchString) > 20:
#             raise Exception("searchString is too short. Must be at least 2 characters")
#
#         # check for possible sql attacks etc...
#         if '}' in searchString or '{' in searchString or ';' in searchString:
#             raise Exception("illegal characters in searchString")
#
#         from django.db import connection
#
#         cursor = connection.cursor()
#
#         sql = """
#         SELECT search_string, text_type, external_id, st_asgeojson(st_PointOnSurface(geom)) AS center, layer, building_id, 0 AS resultType, id
#                 FROM geodata.search_index_v
#                 WHERE upper(external_id) LIKE %(search_string)s
#                 ORDER BY search_string DESC, length(search_string) LIMIT 1
#         """
#
#         searchString2 = "%" + searchString.upper() + "%"
#
#         cursor.execute(sql, {"search_string": searchString2})
#
#         dbRows = cursor.fetchall()
#
#         if len(dbRows) > 0:
#             geojson_data = {"type": "Feature"}
#
#             for row in dbRows:
#                 room_center_coord = json.loads(row[3])
#                 geojson_data["geometry"] = room_center_coord
#                 point_attributes = {"aks": row[2],
#                                     "floor": int(row[4]), "building": row[5]
#                                     }
#                 geojson_data["properties"] = point_attributes
#             return Response(geojson_data)
#         else:
#             error_data = {"error": "Sorry the BIG_PK  ie AKS nummer was not found in the database"}
#             return Response(error_data)
#     else:
#         # raise Exception("wrong IP! your ip is : " + ip_addr)
#         # return HttpResponseForbidden()
#         raise PermissionDenied