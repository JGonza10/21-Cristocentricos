// Dónde corre la app: «nube» (Railway, solo para vigilar el avance) o «local» (la laptop, que hace todo).
// En la nube no hay videos ni archivos: grabar, editar reels y descargar Material se hace en la laptop.
let nube = false

export function fijarModo(modo) {
  nube = modo === 'nube'
}

export const enNube = () => nube

export const AVISO_LAPTOP = 'Esto se hace en la laptop: los videos y archivos no se suben a internet.'
