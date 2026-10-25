/* App de clientes. Cada ruta apunta a la pantalla (vista) que la dibuja.
   El orden importa: las rutas más concretas van primero. */
import { startRouter } from '../core/router.js';
import { viewReservationEdit } from './bookings.js';
import { viewCustomerHome } from './home.js';
import { viewCustomers } from './customers.js';
import { viewRestaurant } from './restaurant.js';

startRouter([
  ['', viewCustomers],
  ['c/:cid/reserva/:resid', viewReservationEdit],
  ['c/:cid/r/:rid/:tab?', viewRestaurant],
  ['c/:cid/:tab?', viewCustomerHome],
]);
