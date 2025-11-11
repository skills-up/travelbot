'use strict';

const identity = {
  type: 'object',
  required: ['channel', 'userId'],
  properties: {
    channel: { type: 'string', enum: ['whatsapp_group', 'web'] },
    groupId: { type: 'string', nullable: true },
    userId: { type: 'string' },
    travelerId: { type: 'string', nullable: true }
  }
};

const messageSchema = {
  body: {
    type: 'object',
    required: ['identity', 'text'],
    properties: {
      identity,
      text: { type: 'string', minLength: 1 }
    }
  },
  response: {
    200: {
      type: 'object',
      required: ['message'],
      properties: {
        message: { type: 'string' },
        confirmReady: { type: 'boolean' },
        state: {
          type: 'object',
          properties: {
            itinerary: {
              type: 'object',
              properties: {
                flightOptions: { type: 'array', items: { type: 'object' } },
                hotelOptions: { type: 'array', items: { type: 'object' } },
                selectedFlight: { type: 'object', nullable: true },
                selectedHotel: { type: 'object', nullable: true },
                holdUntil: { type: 'string', format: 'date-time', nullable: true },
                confirmReady: { type: 'boolean' },
                pnr: { type: 'string', nullable: true },
                ticketNumbers: { type: 'array', items: { type: 'string' } },
                hotelConfirmation: { type: 'string', nullable: true }
              }
            }
          }
        }
      }
    }
  }
};

module.exports = {
  messageSchema,
  identitySchema: identity
};
