#!/usr/bin/python
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Library General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# ExpectedResults.py
# Copyright (C) 2011 Simon Newton
#
# Expected result classes are broken down as follows:
#
# BaseExpectedResult - the base class
#  BroadcastResult   - expects the request to be broadcast
#  SuccessfulResult  - expects a well formed response from the device
#   NackResult       - parent NACK class
#    NackGetResult   - expects GET_COMMAND_RESPONSE with a NACK
#    NackSetResult   - expects SET_COMMAND_RESPONSE with a NACK
#   AckResult        - parent ACK class
#    AckGetResult    - expects GET_COMMAND_RESPONSE with an ACK
#    AckSetResult    - expects SET_COMMAND_RESPONSE with an ACK
#   QueuedMessageResult - expects an ACK or NACK for any PID other than
#                         QUEUED_MESSAGE


from ola.OlaClient import OlaClient
from ola.PidStore import RDM_GET, RDM_SET, GetStore

COMMAND_CLASS_DICT = {
    RDM_GET: 'Get',
    RDM_SET: 'Set',
}

def _CommandClassToString(command_class):
  return COMMAND_CLASS_DICT[command_class]


class BaseExpectedResult(object):
  """The base class for expected results."""
  def __init__(self,
               action = None,
               warning = None,
               advisory = None):
    """Create the base expected result object.

    Args:
      action: The action to run if this result matches
      warning: A warning message to log is this result matches
      advisory: An advisory message to log is this result matches
    """
    self._action = action
    self._warning_messae = warning
    self._advisory_message = advisory

  @property
  def action(self):
    return self._action

  @property
  def warning(self):
    return self._warning_messae

  @property
  def advisory(self):
    return self._advisory_message

  def Matches(self, status, command_class, pid_value, fields):
    """Check if the response we receieved matches this object.

    Args:
      status: An RDMRequestStatus object
      command_class: RDM_GET or RDM_SET
      pid: The value of the pid that was returned, or None if we didn't get a
        valid response.
      fields: A dict of field name : value mappings that were present in the
        response.
    """
    raise TypeError('Base method called')


class BroadcastResult(BaseExpectedResult):
  """This checks that the request was broadcast."""
  def __str__(self):
    return 'RDM_WAS_BROADCAST'

  def Matches(self, status, command_class, pid_value, fields):
    return OlaClient.RDM_WAS_BROADCAST == status.response_code


class SuccessfulResult(BaseExpectedResult):
  """This checks that we received a valid response from the device.

  This doesn't check that the response was a certain type, but simply that the
  message was formed correctly. Other classes inherit from this an perform more
  specific checking.
  """
  def __str__(self):
    return 'RDM_COMPLETED_OK'

  def Matches(self, status, command_class, pid_value, fields):
    return status.response_code == OlaClient.RDM_COMPLETED_OK


class QueuedMessageResult(SuccessfulResult):
  """This checks for a valid response to a QUEUED_MESSAGE request."""
  def __str__(self):
    return 'It\'s complicated'

  def Matches(self, status, command_class, pid_value, fields):
    ok = super(QueuedMessageResult, self).Matches(status,
                                                  command_class,
                                                  pid_value,
                                                  fields)

    if not ok:
      return False

    pid_store = GetStore()
    queued_message_pid = pid_store.GetName('QUEUED_MESSAGE')

    return ((status.response_type == OlaClient.RDM_NACK_REASON or
             status.response_type == OlaClient.RDM_ACK) and
            pid_value != queued_message_pid.value)


class NackResult(SuccessfulResult):
  """This checks that the device nacked the request."""
  def __init__(self,
               command_class,
               pid_id,
               nack_reason,
               action = None,
               warning = None,
               advisory = None):
    """Create an NackResult object.

    Args:
      command_class: RDM_GET or RDM_SET
      pid_id: The pid id we expect to have been nack'ed
      nack_reason: The RDMNack object we expect.
      action: The action to run if this result matches
      warning: A warning message to log is this result matches
      advisory: An advisory message to log is this result matches
    """
    super(NackResult, self).__init__(action, warning, advisory)

    self._command_class = command_class
    self._pid_id = pid_id
    self._nack_reason = nack_reason

  def __str__(self):
    return ('CC: %s, PID 0x%04hx, NACK %s' %
            (_CommandClassToString(self._command_class),
             self._pid_id,
             self._nack_reason))

  def Matches(self, status, command_class, pid_value, fields):
    ok = super(NackResult, self).Matches(status,
                                         command_class,
                                         pid_value,
                                         fields)

    return (ok and
            status.response_type == OlaClient.RDM_NACK_REASON and
            command_class == self._command_class and
            self._pid_id == pid_value and
            self._nack_reason == status.nack_reason)


class NackGetResult(NackResult):
  """This checks that the device nacked a GET request."""
  def __init__(self,
               pid_id,
               nack_reason,
               action = None,
               warning = None,
               advisory = None):
    """Create an expected result object which is a NACK for a GET request.

    Args:
      pid_id: The pid id we expect to have been nack'ed
      nack_reason: The RDMNack object we expect.
      action: The action to run if this result matches
      warning: A warning message to log is this result matches
      advisory: An advisory message to log is this result matches
    """
    super(NackGetResult, self).__init__(RDM_GET,
                                        pid_id,
                                        nack_reason,
                                        action,
                                        warning,
                                        advisory)


class NackSetResult(NackResult):
  """This checks that the device nacked a SET request."""
  def __init__(self,
               pid_id,
               nack_reason,
               action = None,
               warning = None,
               advisory = None):
    """Create an expected result object which is a NACK for a SET request.

    Args:
      pid_id: The pid id we expect to have been nack'ed
      nack_reason: The RDMNack object we expect.
      action: The action to run if this result matches
      warning: A warning message to log is this result matches
      advisory: An advisory message to log is this result matches
    """
    super(NackSetResult, self).__init__(RDM_SET,
                                        pid_id,
                                        nack_reason,
                                        action,
                                        warning,
                                        advisory)


class AckResult(SuccessfulResult):
  """This checks that the device ack'ed the request."""
  def __init__(self,
               command_class,
               pid_id,
               field_names = [],
               field_values = {},
               action = None,
               warning = None,
               advisory = None):
    """Create an expected result object that matches an ACK.

    Args:
      command_class: RDM_GET or RDM_SET
      pid_id: The pid id we expect
      field_names: Check that these fields are present in the response
      field_dict: Check that fields & values are present in the response
      action: The action to run if this result matches
      warning: A warning message to log is this result matches
      advisory: An advisory message to log is this result matches
    """
    super(AckResult, self).__init__(action, warning, advisory)

    self._command_class = command_class
    self._pid_id = pid_id
    self._field_names = field_names
    self._field_values = field_values

  def __str__(self):
    return ('CC: %s, PID 0x%04hx, ACK, fields %s, values %s' % (
            _CommandClassToString(self._command_class),
            self._pid_id,
            self._field_names,
            self._field_values))

  def Matches(self, status, command_class, pid_value, fields):
    ok = super(AckResult, self).Matches(status,
                                          command_class,
                                          pid_value,
                                          fields)
    if (not ok or
        status.response_type != OlaClient.RDM_ACK or
        command_class != self._command_class or
        self._pid_id != pid_value):
      return False

    # fields may be either a list of dicts, or a dict
    if isinstance(fields, list):
      for item in fields:
        field_keys = set(item.keys())
        for field in self._field_names:
          if field not in field_keys:
            return False
    else:
      field_keys = set(fields.keys())
      for field in self._field_names:
        if field not in field_keys:
          return False

    for field, value in self._field_values.iteritems():
      if field not in fields:
        return False
      if value != fields[field]:
        return False
    return True


class AckGetResult(AckResult):
  """This checks that the device ack'ed a GET request."""
  def __init__(self,
               pid_id,
               field_names = [],
               field_values = {},
               action = None,
               warning = None,
               advisory = None):
    """Create an expected result object which is an ACK for a GET request.

    Args:
      pid_id: The pid id we expect
      field_names: Check that these fields are present in the response
      field_dict: Check that fields & values are present in the response
      action: The action to run if this result matches
      warning: A warning message to log is this result matches
      advisory: An advisory message to log is this result matches
    """
    super(AckGetResult, self).__init__(RDM_GET,
                                       pid_id,
                                       field_names,
                                       field_values,
                                       action,
                                       warning,
                                       advisory)


class AckSetResult(AckResult):
  """This checks that the device ack'ed a SET request."""
  def __init__(self,
               pid_id,
               field_names = [],
               field_values = {},
               action = None,
               warning = None,
               advisory = None):
    """Create an expected result object which is an ACK for a SET request.

    Args:
      pid_id: The pid id we expect
      field_names: Check that these fields are present in the response
      field_dict: Check that fields & values are present in the response
      action: The action to run if this result matches
      warning: A warning message to log is this result matches
      advisory: An advisory message to log is this result matches
    """
    super(AckSetResult, self).__init__(RDM_SET,
                                       pid_id,
                                       field_names,
                                       field_values,
                                       action,
                                       warning,
                                       advisory)