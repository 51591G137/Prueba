/* Menú del restaurante: carta, alta de platos, edición y borrado. */
import { api } from '../core/api.js';
import { field, h, loading } from '../core/dom.js';
import { leave } from '../core/router.js';
import { confirmDialog, guarded, onSubmit, setScreen, toast } from '../core/ui.js';
import { menuList } from '../components/menu-list.js';

export async function menuTab({ uid, rid, box, stale }) {
  const holder = h('div');

  async function refresh() {
    const items = await api.get(`/api/restaurants/${rid}/menu`);
    if (stale()) return;
    holder.replaceChildren(
      menuList(items, 'El menú está vacío. Añade el primer plato abajo.', { hrefFor: (item) => `#/u/${uid}/r/${rid}/plato/${item.id}` }),
    );
  }

  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data, f) => {
        await api.post(`/api/restaurants/${rid}/menu`, data);
        f.reset();
        toast('Añadido al menú');
        await refresh();
      }),
    },
    h('h2', null, 'Nuevo plato'),
    field('Nombre', h('input', { name: 'name', type: 'text', required: true, maxlength: 120, autocomplete: 'off' })),
    field('Descripción (opcional)', h('input', { name: 'description', type: 'text', maxlength: 300, autocomplete: 'off' })),
    field('Precio (€)', h('input', { name: 'price', type: 'number', required: true, min: 0, step: '0.01', inputmode: 'decimal' })),
    h('button', { class: 'btn', type: 'submit' }, 'Añadir al menú'),
  );

  box.append(holder, form);
  await refresh();
}

export async function viewItemEdit({ params, stale }) {
  const { uid, rid, iid } = params;
  const back = `#/u/${uid}/r/${rid}/menu`;
  setScreen('Editar plato', back, loading());
  const item = await api.get(`/api/menu/${iid}`);
  if (stale()) return;

  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data) => {
        await api.patch(`/api/menu/${iid}`, data);
        toast('Cambios guardados');
        leave(back);
      }),
    },
    h('h2', null, item.name),
    field('Nombre', h('input', { name: 'name', type: 'text', value: item.name, required: true, maxlength: 120, autocomplete: 'off' })),
    field('Descripción (opcional)', h('input', { name: 'description', type: 'text', value: item.description || '', maxlength: 300, autocomplete: 'off' })),
    field('Precio (€)', h('input', { name: 'price', type: 'number', value: item.price.toFixed(2), required: true, min: 0, step: '0.01', inputmode: 'decimal' })),
    h('p', { class: 'muted small' }, 'Si cambias el precio, las comandas ya hechas conservan el precio con el que se pidieron.'),
    h('button', { class: 'btn', type: 'submit' }, 'Guardar cambios'),
  );

  const remove = guarded(async () => {
    const confirmed = await confirmDialog({
      title: `¿Borrar «${item.name}»?`,
      message: 'Dejará de aparecer en el menú. Las facturas ya cobradas no cambian.',
      confirmLabel: 'Borrar plato',
      danger: true,
    });
    if (!confirmed) return;
    await api.del(`/api/menu/${iid}`);
    toast('Plato borrado');
    leave(back);
  });

  setScreen(
    'Editar plato',
    back,
    form,
    h('div', { class: 'danger-zone' }, h('button', { class: 'btn danger', type: 'button', onclick: remove }, 'Borrar plato')),
  );
}
