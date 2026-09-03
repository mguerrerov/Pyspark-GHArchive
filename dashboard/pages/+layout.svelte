<script>
	// Copia del layout por defecto de Evidence, solo para poder anadir CSS
	// global: el menu lateral lleva la clase `capitalize` y en espanol deja
	// "Sobre Los Datos". Se anula la transformacion.
	import '@evidence-dev/tailwind/fonts.css';
	import '../app.css';
	import { EvidenceDefaultLayout } from '@evidence-dev/core-components';
	export let data;
</script>

<EvidenceDefaultLayout {data}>
	<slot slot="content" />
</EvidenceDefaultLayout>

<style>
	:global(aside a.capitalize) {
		text-transform: none;
	}
</style>
