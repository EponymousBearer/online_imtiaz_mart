# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: order.proto
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
    'order.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0border.proto\"n\n\x05Order\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x0f\n\x07user_id\x18\x02 \x01(\x05\x12\x12\n\nproduct_id\x18\x03 \x01(\x05\x12\x10\n\x08quantity\x18\x04 \x01(\x05\x12\x0e\n\x06status\x18\x05 \x01(\t\x12\x12\n\norder_date\x18\x06 \x01(\t\"s\n\x08\x43\x61rtItem\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x0f\n\x07user_id\x18\x02 \x01(\x05\x12\x12\n\nproduct_id\x18\x03 \x01(\x05\x12\x10\n\x08quantity\x18\x04 \x01(\x05\x12\x10\n\x08\x61\x64\x64\x65\x64_at\x18\x05 \x01(\t\x12\x12\n\nupdated_at\x18\x06 \x01(\t\"-\n\rCartItemAdded\x12\x1c\n\tcart_item\x18\x01 \x01(\x0b\x32\t.CartItem\"/\n\x0f\x43\x61rtItemUpdated\x12\x1c\n\tcart_item\x18\x01 \x01(\x0b\x32\t.CartItem\"/\n\x0f\x43\x61rtItemRemoved\x12\x1c\n\tcart_item\x18\x01 \x01(\x0b\x32\t.CartItemb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'order_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_ORDER']._serialized_start=15
  _globals['_ORDER']._serialized_end=125
  _globals['_CARTITEM']._serialized_start=127
  _globals['_CARTITEM']._serialized_end=242
  _globals['_CARTITEMADDED']._serialized_start=244
  _globals['_CARTITEMADDED']._serialized_end=289
  _globals['_CARTITEMUPDATED']._serialized_start=291
  _globals['_CARTITEMUPDATED']._serialized_end=338
  _globals['_CARTITEMREMOVED']._serialized_start=340
  _globals['_CARTITEMREMOVED']._serialized_end=387
# @@protoc_insertion_point(module_scope)
