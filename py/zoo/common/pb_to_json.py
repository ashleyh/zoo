# pb_to_json.py - turns protobuf objects into plain python
# dictionaries and things suitable for json serialisation
# 
# Copyright 2011 Ashley Hewson
# 
# This file is part of Compiler Zoo.
# 
# Compiler Zoo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Compiler Zoo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Compiler Zoo.  If not, see <http://www.gnu.org/licenses/>.

from google.protobuf.descriptor import FieldDescriptor

def pb_value_to_json(descriptor, value):
    if descriptor.type == FieldDescriptor.TYPE_MESSAGE:
        return pb_to_json(value)
    else:
        #XXX: does this actually work?
        return value
    
def pb_field_to_json(descriptor, value):
    if descriptor.label == FieldDescriptor.LABEL_REPEATED:
        return [pb_value_to_json(descriptor, x) for x in value]
    else:
        return pb_value_to_json(descriptor, value)

def pb_to_json(pb):
    obj = {}
    for descriptor, value in pb.ListFields():
        obj[descriptor.name] = pb_field_to_json(descriptor, value)
    return obj
