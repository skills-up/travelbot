'use strict';

const CITY_ALIASES = new Map([
  ['mum', 'BOM'],
  ['mumbai', 'BOM'],
  ['bom', 'BOM'],
  ['del', 'DEL'],
  ['delhi', 'DEL'],
  ['new delhi', 'DEL']
]);

const MONTHS = new Map([
  ['jan', 0],
  ['feb', 1],
  ['mar', 2],
  ['apr', 3],
  ['may', 4],
  ['jun', 5],
  ['jul', 6],
  ['aug', 7],
  ['sep', 8],
  ['sept', 8],
  ['oct', 9],
  ['nov', 10],
  ['dec', 11]
]);

const DEFAULT_PROFILE = {
  name: 'Default Traveler',
  seat_pref: 'AISLE',
  meal_pref: 'VEG',
  class_pref: 'ECONOMY',
  airlines: ['AI', 'UK']
};

function keyFor(channel, groupId, userId) {
  if (channel === 'whatsapp_group') {
    return `${channel}:${groupId}`;
  }
  return `${channel}:${userId}`;
}

function normaliseCode(code) {
  return code ? code.toUpperCase() : null;
}

function formatTime(hours, minutes, meridiem) {
  let h = Number(hours);
  let m = Number(minutes || 0);
  if (meridiem) {
    const upper = meridiem.toUpperCase();
    if (upper === 'PM' && h !== 12) {
      h += 12;
    }
    if (upper === 'AM' && h === 12) {
      h = 0;
    }
  }
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
}

function isoDateFromParts(monthName, day, explicitYear, now) {
  const monthIdx = MONTHS.get(monthName.slice(0, 3).toLowerCase());
  if (monthIdx === undefined) {
    return null;
  }
  const year = explicitYear ? Number(explicitYear) : now.getFullYear();
  const date = new Date(Date.UTC(year, monthIdx, Number(day)));
  return date.toISOString().slice(0, 10);
}

function addMinutes(date, minutes) {
  return new Date(date.getTime() + minutes * 60000);
}

function clone(obj) {
  return obj ? JSON.parse(JSON.stringify(obj)) : obj;
}

class ChatbotService {
  constructor(options = {}) {
    this.nowProvider = options.nowProvider || (() => new Date());
    this.profiles = options.profiles || new Map();
    this.sessions = new Map();
  }

  async handleMessage(payload) {
    const { identity, text } = payload;
    const cleanedText = text.trim();
    const state = this.#getOrCreateState(identity);
    state.lastInbound = cleanedText;

    if (/^F\?$/i.test(cleanedText)) {
      return this.#respond(state, 'Fare rules available on request. Reply CONFIRM with a code to proceed.');
    }
    if (/^H\?$/i.test(cleanedText)) {
      return this.#respond(state, 'Rate rules available on request. Reply CONFIRM with a code to proceed.');
    }

    if (/^CONFIRM\b/i.test(cleanedText)) {
      return this.#handleConfirm(state, cleanedText, identity.userId);
    }

    const picks = [...cleanedText.matchAll(/\b([FH])(\d)\b/gi)];
    if (picks.length > 0) {
      return this.#handleSelections(state, picks.map((match) => match[1].toUpperCase() + match[2]));
    }

    return this.#handleNewInstruction(state, cleanedText);
  }

  #respond(state, message) {
    state.lastOutbound = message;
    return {
      message,
      confirmReady: state.itinerary.confirmReady,
      state: this.#publicState(state)
    };
  }

  #publicState(state) {
    return {
      itinerary: {
        flightOptions: state.itinerary.flightOptions.map((opt) => ({ ...opt })),
        hotelOptions: state.itinerary.hotelOptions.map((opt) => ({ ...opt })),
        selectedFlight: clone(state.itinerary.selectedFlight),
        selectedHotel: clone(state.itinerary.selectedHotel),
        holdUntil: state.itinerary.holdUntil ? state.itinerary.holdUntil.toISOString() : null,
        confirmReady: state.itinerary.confirmReady,
        pnr: state.itinerary.pnr,
        ticketNumbers: [...state.itinerary.ticketNumbers],
        hotelConfirmation: state.itinerary.hotelConfirmation
      }
    };
  }

  #getOrCreateState(identity) {
    const key = keyFor(identity.channel, identity.groupId, identity.userId);
    if (this.sessions.has(key)) {
      const existing = this.sessions.get(key);
      existing.identity = { ...existing.identity, ...identity };
      return existing;
    }
    const profile = this.#loadProfile(identity);
    const state = {
      identity: { ...identity },
      profile,
      itinerary: {
        flightOptions: [],
        hotelOptions: [],
        selectedFlight: null,
        selectedHotel: null,
        confirmReady: false,
        holdUntil: null,
        pnr: null,
        ticketNumbers: [],
        hotelConfirmation: null
      },
      lastInbound: null,
      lastOutbound: null
    };
    this.sessions.set(key, state);
    return state;
  }

  #loadProfile(identity) {
    if (identity && identity.userId && this.profiles.has(identity.userId)) {
      return { ...DEFAULT_PROFILE, ...this.profiles.get(identity.userId) };
    }
    return { ...DEFAULT_PROFILE, userId: identity.userId };
  }

  #handleNewInstruction(state, text) {
    const now = this.nowProvider();
    const intent = this.#parseIntent(text, now);
    if (!intent.wantFlights && !intent.wantHotels) {
      return this.#respond(state, 'I can help with flights and hotels. Please share your travel details.');
    }

    if (intent.wantFlights) {
      state.itinerary.flightOptions = this.#generateFlightOptions(intent);
    }
    if (intent.wantHotels) {
      state.itinerary.hotelOptions = this.#generateHotelOptions(intent);
    }
    state.itinerary.selectedFlight = null;
    state.itinerary.selectedHotel = null;
    state.itinerary.confirmReady = false;
    state.itinerary.holdUntil = null;
    const responseParts = [];
    if (intent.wantFlights && state.itinerary.flightOptions.length > 0) {
      responseParts.push(this.#formatFlightOptions(state.itinerary.flightOptions));
    }
    if (intent.wantHotels && state.itinerary.hotelOptions.length > 0) {
      responseParts.push(this.#formatHotelOptions(state.itinerary.hotelOptions, intent));
    }
    return this.#respond(state, responseParts.join('\n\n'));
  }

  #handleSelections(state, codes) {
    if (state.itinerary.flightOptions.length === 0 && state.itinerary.hotelOptions.length === 0) {
      return this.#respond(state, 'Please share your travel details first so I can search options.');
    }
    for (const code of codes) {
      if (code.startsWith('F')) {
        const index = Number(code.slice(1)) - 1;
        const option = state.itinerary.flightOptions[index];
        if (option) {
          state.itinerary.selectedFlight = { ...option };
          state.itinerary.selectedFlight.code = normaliseCode(code);
        }
      }
      if (code.startsWith('H')) {
        const index = Number(code.slice(1)) - 1;
        const option = state.itinerary.hotelOptions[index];
        if (option) {
          state.itinerary.selectedHotel = { ...option };
          state.itinerary.selectedHotel.code = normaliseCode(code);
        }
      }
    }
    if (!state.itinerary.selectedFlight && !state.itinerary.selectedHotel) {
      return this.#respond(state, 'Please pick a valid option using F1/F2 or H1/H2 codes.');
    }
    state.itinerary.holdUntil = addMinutes(this.nowProvider(), 45);
    state.itinerary.confirmReady = true;
    const message = this.#formatConfirmation(state);
    return this.#respond(state, message);
  }

  #handleConfirm(state, text, senderUserId) {
    if (!state.itinerary.confirmReady) {
      return this.#respond(state, 'Please select an option first (e.g., F1 or H1).');
    }
    const intent = this.#parseConfirmCodes(text);
    if (intent.codes.length === 0) {
      return this.#respond(state, 'Please specify which options to confirm, e.g., CONFIRM F2 H1.');
    }
    const allowedTraveler = state.identity.travelerId || state.identity.userId;
    if (senderUserId !== allowedTraveler) {
      return this.#respond(state, 'Only the mapped traveler can confirm the trip.');
    }
    const now = this.nowProvider();
    if (state.itinerary.holdUntil && now > state.itinerary.holdUntil) {
      this.#refreshOptions(state);
      const parts = ['Hold expired. Updating fares. Please review new options.'];
      if (state.itinerary.flightOptions.length > 0) {
        parts.push(this.#formatFlightOptions(state.itinerary.flightOptions));
      }
      if (state.itinerary.hotelOptions.length > 0) {
        parts.push(this.#formatHotelOptions(state.itinerary.hotelOptions, {}));
      }
      return this.#respond(state, parts.join('\n\n'));
    }

    if (state.itinerary.selectedFlight && !intent.codes.includes(state.itinerary.selectedFlight.code)) {
      return this.#respond(state, `Please confirm the selected flight using ${state.itinerary.selectedFlight.code}.`);
    }
    if (state.itinerary.selectedHotel && !intent.codes.includes(state.itinerary.selectedHotel.code)) {
      return this.#respond(state, `Please confirm the selected hotel using ${state.itinerary.selectedHotel.code}.`);
    }

    if (state.itinerary.selectedFlight) {
      this.#bookFlight(state);
    }
    if (state.itinerary.selectedHotel) {
      this.#bookHotel(state);
    }
    state.itinerary.confirmReady = false;
    const message = this.#formatFinalMessage(state);
    return this.#respond(state, message);
  }

  #parseConfirmCodes(text) {
    const codes = [];
    const matches = text.toUpperCase().match(/[FH]\d+/g);
    if (matches) {
      for (const code of matches) {
        if (!codes.includes(code)) {
          codes.push(code);
        }
      }
    }
    return { codes };
  }

  #parseIntent(text, now) {
    const lower = text.toLowerCase();
    const intent = {
      wantFlights: /(flight|flt|fly|air)/i.test(text),
      wantHotels: /(hotel|stay|room)/i.test(text),
      origin: null,
      destination: null,
      departDate: null,
      timeFrom: null,
      timeTo: null,
      checkIn: null,
      checkOut: null,
      landmark: null
    };

    const routeMatch = lower.match(/([a-z]{3,})(?:\s*[-→to]+\s*)([a-z]{3,})/);
    if (routeMatch) {
      const [, fromRaw, toRaw] = routeMatch;
      intent.origin = this.#resolveCity(fromRaw);
      intent.destination = this.#resolveCity(toRaw);
      intent.wantFlights = Boolean(intent.origin && intent.destination);
    }

    const dateRegex = /(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\.?\s*(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(\d{4}))?/gi;
    let match;
    const dates = [];
    while ((match = dateRegex.exec(text)) !== null) {
      dates.push(isoDateFromParts(match[1], match[2], match[3], now));
    }
    if (dates.length > 0) {
      intent.departDate = dates[0];
    }
    if (dates.length > 1) {
      intent.checkIn = dates[1];
      intent.checkOut = dates[2] || dates[1];
    }

    if (!intent.checkIn) {
      const stayRange = text.match(/(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\.?\s*(\d{1,2})(?:st|nd|rd|th)?\s*(?:-|–)\s*(\d{1,2})(?:st|nd|rd|th)?/i);
      if (stayRange) {
        const baseDate = isoDateFromParts(stayRange[1], stayRange[2], null, now);
        if (baseDate) {
          const [year, month] = baseDate.split('-');
          intent.checkIn = baseDate;
          intent.checkOut = `${year}-${month}-${stayRange[3].padStart(2, '0')}`;
          intent.wantHotels = true;
        }
      }
    }

    const rangeMatch = text.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*(?:-|to|–)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i);
    if (rangeMatch) {
      intent.timeFrom = formatTime(rangeMatch[1], rangeMatch[2], rangeMatch[3]);
      intent.timeTo = formatTime(rangeMatch[4], rangeMatch[5], rangeMatch[6]);
    }

    if (/aerocity/i.test(text)) {
      intent.landmark = 'Aerocity';
      intent.wantHotels = true;
    }

    const simpleRange = text.match(/\b(\d{1,2})\s*-\s*(\d{1,2})\b/);
    if (!rangeMatch && simpleRange && intent.checkIn) {
      const [, startDay, endDay] = simpleRange;
      const [year, month] = intent.checkIn.split('-');
      intent.checkIn = `${year}-${month}-${startDay.padStart(2, '0')}`;
      intent.checkOut = `${year}-${month}-${endDay.padStart(2, '0')}`;
    }

    return intent;
  }

  #resolveCity(token) {
    const lookup = token.replace(/[^a-z]/gi, '').toLowerCase();
    return CITY_ALIASES.get(lookup) || token.toUpperCase();
  }

  #generateFlightOptions(intent) {
    const origin = intent.origin || 'BOM';
    const destination = intent.destination || 'DEL';
    const depart = intent.departDate || this.nowProvider().toISOString().slice(0, 10);
    return [
      {
        code: 'F1',
        airline: 'AI',
        flight_number: '678',
        origin,
        destination,
        depart_date: depart,
        depart: intent.timeFrom || '16:05',
        arrive: intent.timeTo || '18:15',
        cabin: 'ECONOMY',
        nonstop: true,
        baggage: '25kg',
        currency: 'INR',
        amount: 7900,
        offerId: 'OFFER-F1'
      },
      {
        code: 'F2',
        airline: 'UK',
        flight_number: '933',
        origin,
        destination,
        depart_date: depart,
        depart: intent.timeFrom || '15:20',
        arrive: intent.timeTo || '17:30',
        cabin: 'ECONOMY',
        nonstop: true,
        baggage: '15kg',
        currency: 'INR',
        amount: 8200,
        offerId: 'OFFER-F2'
      },
      {
        code: 'F3',
        airline: '6E',
        flight_number: '5313',
        origin,
        destination,
        depart_date: depart,
        depart: intent.timeFrom || '15:45',
        arrive: intent.timeTo || '18:50',
        cabin: 'PREMIUM_ECONOMY',
        nonstop: false,
        stops: '1 stop',
        baggage: '15kg',
        currency: 'INR',
        amount: 6950,
        offerId: 'OFFER-F3'
      }
    ];
  }

  #generateHotelOptions(intent) {
    const checkIn = intent.checkIn || intent.departDate || this.nowProvider().toISOString().slice(0, 10);
    const checkOut = intent.checkOut || checkIn;
    const landmark = intent.landmark || 'Aerocity';
    return [
      {
        code: 'H1',
        name: 'JW Marriott',
        rating: 4.8,
        currency: 'INR',
        amount: 13500,
        board: 'BB',
        check_in: checkIn,
        check_out: checkOut,
        landmark,
        rateId: 'RATE-H1'
      },
      {
        code: 'H2',
        name: 'Aloft',
        rating: 4.3,
        currency: 'INR',
        amount: 8900,
        board: 'Room only',
        check_in: checkIn,
        check_out: checkOut,
        landmark,
        rateId: 'RATE-H2'
      },
      {
        code: 'H3',
        name: 'Andaz',
        rating: 4.6,
        currency: 'INR',
        amount: 12800,
        board: 'BB',
        check_in: checkIn,
        check_out: checkOut,
        landmark,
        rateId: 'RATE-H3'
      }
    ];
  }

  #formatFlightOptions(options) {
    const lines = ['Flights (priced now):'];
    for (const option of options) {
      lines.push(`[ ${option.code} ] ${option.airline} ${option.flight_number} ${option.origin} ${option.depart} → ${option.destination} ${option.arrive}`);
      const nonstopText = option.nonstop ? 'Nonstop' : option.stops || '1 stop';
      lines.push(`${option.cabin.replace('_', ' ')} • ${nonstopText} • ${option.baggage} • ₹${option.amount}`);
      lines.push('');
    }
    lines.push('Reply: F1/F2/F3. Send F? for fare rules.');
    return lines.join('\n').trim();
  }

  #formatHotelOptions(options, intent) {
    const headerParts = ['Hotels'];
    const landmark = intent.landmark || (options[0] && options[0].landmark);
    const checkIn = intent.checkIn || (options[0] && options[0].check_in);
    const checkOut = intent.checkOut || (options[0] && options[0].check_out);
    if (landmark) {
      headerParts.push(`(${landmark}`);
      if (checkIn && checkOut) {
        headerParts[headerParts.length - 1] += `, ${checkIn}–${checkOut})`;
      } else {
        headerParts[headerParts.length - 1] += ')';
      }
    }
    const lines = [headerParts.join(' ') + ':'];
    for (const option of options) {
      lines.push(`[ ${option.code} ] ${option.name} • ${option.rating}★ • ₹${option.amount} • ${option.board}`);
    }
    lines.push('Reply: H1/H2/H3. Send H? for rate rules.');
    return lines.join('\n');
  }

  #formatConfirmation(state) {
    const lines = ['Please confirm:'];
    const flight = state.itinerary.selectedFlight;
    const hotel = state.itinerary.selectedHotel;
    if (flight) {
      lines.push(`${flight.origin}→${flight.destination} ${flight.depart_date} • ${flight.airline} ${flight.flight_number} • ${flight.depart}–${flight.arrive}`);
      lines.push(`Traveler: ${state.profile.name} • ${flight.cabin.replace('_', ' ')} • ${state.profile.seat_pref} • ${state.profile.meal_pref}`);
      if (state.itinerary.holdUntil) {
        const hold = state.itinerary.holdUntil;
        lines.push(`Fare ₹${flight.amount} (hold until ${hold.getHours().toString().padStart(2, '0')}:${hold.getMinutes().toString().padStart(2, '0')})`);
      }
    }
    if (hotel) {
      lines.push(`Hotel: ${hotel.name} • ${hotel.check_in}–${hotel.check_out} • ₹${hotel.amount}`);
    }
    const codes = [];
    if (flight) {
      codes.push(flight.code);
    }
    if (hotel) {
      codes.push(hotel.code);
    }
    lines.push(`Type: CONFIRM ${codes.join(' ')}`);
    return lines.join('\n');
  }

  #formatFinalMessage(state) {
    const lines = ['Booking complete:'];
    if (state.itinerary.pnr) {
      lines.push(`Flight PNR: ${state.itinerary.pnr}`);
    }
    if (state.itinerary.ticketNumbers.length > 0) {
      lines.push(`Tickets: ${state.itinerary.ticketNumbers.join(', ')}`);
    }
    if (state.itinerary.hotelConfirmation) {
      lines.push(`Hotel confirmation: ${state.itinerary.hotelConfirmation}`);
    }
    return lines.join('\n');
  }

  #bookFlight(state) {
    state.itinerary.pnr = 'PNR123';
    state.itinerary.ticketNumbers = ['2201234567890'];
  }

  #bookHotel(state) {
    state.itinerary.hotelConfirmation = 'HOTEL123';
  }

  #refreshOptions(state) {
    state.itinerary.selectedFlight = null;
    state.itinerary.selectedHotel = null;
    state.itinerary.confirmReady = false;
    state.itinerary.holdUntil = null;
    state.itinerary.flightOptions = state.itinerary.flightOptions.map((option, index) => ({
      ...option,
      code: `F${index + 1}`,
      amount: option.amount + 500
    }));
    state.itinerary.hotelOptions = state.itinerary.hotelOptions.map((option, index) => ({
      ...option,
      code: `H${index + 1}`,
      amount: option.amount + 300
    }));
  }
}

module.exports = {
  ChatbotService
};
