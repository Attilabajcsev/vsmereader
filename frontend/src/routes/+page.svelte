<script>
	import { goto } from '$app/navigation';
	$effect(() => { goto('/portfolio'); });
</script>

<div class="p-6">Redirecting to Portfolio… <a class="link" href="/portfolio">Go now</a></div>
