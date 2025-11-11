'use strict';

const { messageSchema } = require('../schema/chatbot');
const { ChatbotService } = require('../service/chatbot');

async function chatbotRoutes(fastify, opts = {}) {
  const service = opts.service || new ChatbotService(opts.config);

  fastify.decorate('chatbotService', service);

  fastify.post('/chatbot/message', { schema: messageSchema }, async (request) => {
    return service.handleMessage(request.body);
  });
}

module.exports = chatbotRoutes;
