# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: inventory.proto
# Protobuf Python Version: 5.27.2
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    27,
    2,
    '',
    'inventory.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0finventory.proto\"V\n\tInventory\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x12\n\nproduct_id\x18\x02 \x01(\x05\x12\x13\n\x0bstock_level\x18\x03 \x01(\x05\x12\x14\n\x0clast_updated\x18\x04 \x01(\t\"8\n\x0fInventoryUpdate\x12\x12\n\nproduct_id\x18\x01 \x01(\x05\x12\x11\n\tnew_stock\x18\x02 \x01(\x05\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'inventory_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_INVENTORY']._serialized_start=19
  _globals['_INVENTORY']._serialized_end=105
  _globals['_INVENTORYUPDATE']._serialized_start=107
  _globals['_INVENTORYUPDATE']._serialized_end=163
# @@protoc_insertion_point(module_scope)
