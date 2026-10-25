/* Restaurantes de un usuario: ver los suyos y crear uno nuevo. */
import { api } from '../core/api.js';
import { field, fill, h, loading } from '../core/dom.js';
import { onSubmit, setScreen, toast } from '../core/ui.js';

export async function viewRestaurants({ params, stale }) {
  const { uid } = params;
  setScreen('Cargando…', '#/', loading());
  const user = await api.get(`/api/users/${uid}`);
  if (stale()) return;

  const list = h('ul', { class: 'list' });

  async function refresh() {
    const restaurants = await api.get(`/api/users/${uid}/restaurants`);
    if (stale()) return;
    fill(
      list,
      restaurants,
      (restaurant) =>
        h(
          'li',
          null,
          h(
            'a',
            { class: 'row', href: `#/u/${uid}/r/${restaurant.id}/mesas` },
            h('div', { class: 'grow' }, h('strong', null, restaurant.name), restaurant.address && h('div', { class: 'muted small' }, restaurant.address)),
          ),
        ),
      'Todavía no tienes restaurantes. Crea el primero abajo.',
    );
  }

  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data, f) => {
        await api.post(`/api/users/${uid}/restaurants`, data);
        f.reset();
        toast('Restaurante creado');
        await refresh();
      }),
    },
    h('h2', null, 'Nuevo restaurante'),
    field('Nombre', h('input', { name: 'name', type: 'text', required: true, maxlength: 120, autocomplete: 'off' })),
    field('Dirección (opcional)', h('input', { name: 'address', type: 'text', maxlength: 200, autocomplete: 'off' })),
    h('button', { class: 'btn', type: 'submit' }, 'Crear restaurante'),
  );

  setScreen(`Hola, ${user.username}`, '#/', h('h2', null, 'Tus restaurantes'), list, form);
  await refresh();
}
