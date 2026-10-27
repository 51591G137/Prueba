/* Clientes: identificación con solo número de teléfono (sin contraseñas). */
import { api } from '../core/api.js';
import { field, h } from '../core/dom.js';
import { navigate } from '../core/router.js';
import { onSubmit, setScreen, toast } from '../core/ui.js';

const TITLE = 'Reserva tu mesa';

export async function viewCustomers() {
  const savedId = localStorage.getItem('customer_id');
  const savedName = localStorage.getItem('customer_name');
  const savedPhone = localStorage.getItem('customer_phone') || '';

  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data) => {
        const customer = await api.post('/api/customers', data);
        localStorage.setItem('customer_id', customer.id);
        localStorage.setItem('customer_phone', customer.phone || data.phone);
        localStorage.setItem('customer_name', customer.name);
        toast(`Bienvenido/a, ${customer.name}`);
        navigate(`#/c/${customer.id}`);
      }),
    },
    h('h2', null, 'Identifícate con tu teléfono'),
    h('p', { class: 'muted' }, 'Solo necesitas tu teléfono para reservar mesa y gestionar tus reservas.'),
    field(
      'Teléfono',
      h('input', {
        name: 'phone',
        type: 'tel',
        required: true,
        placeholder: 'Ej. 612345678',
        value: savedPhone,
        autocomplete: 'tel',
      }),
    ),
    field(
      'Nombre (opcional)',
      h('input', {
        name: 'name',
        type: 'text',
        maxlength: 80,
        placeholder: 'Ej. María',
        value: savedName || '',
        autocomplete: 'name',
      }),
    ),
    h('button', { class: 'btn', type: 'submit' }, 'Entrar a reservar'),
  );

  const remembered =
    savedId &&
    h(
      'div',
      { class: 'panel row' },
      h('div', { class: 'grow' }, h('strong', null, `Continuar como ${savedName || savedPhone}`), h('div', { class: 'muted small' }, savedPhone)),
      h('a', { class: 'btn small', href: `#/c/${savedId}` }, 'Entrar'),
    );

  setScreen(TITLE, null, remembered, form);
}
