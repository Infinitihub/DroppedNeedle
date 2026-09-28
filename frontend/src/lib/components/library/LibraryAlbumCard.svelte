<script lang="ts">
	import AlbumImage from '$lib/components/AlbumImage.svelte';
	import { api } from '$lib/api/client';
	import { API } from '$lib/constants';
	import { invalidateQueriesWithPersister } from '$lib/queries/QueryClient';
	import { LibraryQueryKeyFactory } from '$lib/queries/library/LibraryQueryKeyFactory';
	import { toastStore } from '$lib/stores/toast';
	import LibraryFormatBadge from './LibraryFormatBadge.svelte';
	import LocalIdentityBadge from './LocalIdentityBadge.svelte';
	import type { LibraryAlbumSummary } from '$lib/types';
	import { albumHref } from '$lib/utils/entityRoutes';

	interface Props {
		album: LibraryAlbumSummary;
		localRoute?: boolean;
	}

	let { album, localRoute = false }: Props = $props();
	let href = $derived(albumHref(localRoute ? album.id : (album.musicbrainz_release_group_id ?? album.id)));
	let markedFull = $state(false);
	let savingFull = $state(false);
	let seenMark = $state<string | null>(null);

	$effect(() => {
		const signature = `${album.id}:${Boolean(album.marked_full)}`;
		if (savingFull || signature === seenMark) return;
		seenMark = signature;
		markedFull = Boolean(album.marked_full);
	});

	async function toggleFull(event: Event) {
		event.preventDefault();
		event.stopPropagation();
		const next = (event.currentTarget as HTMLInputElement).checked;
		const previous = markedFull;
		markedFull = next;
		savingFull = true;
		try {
			await api.global.put(API.library.markAlbumFull(album.id), { marked_full: next });
			await invalidateQueriesWithPersister({ queryKey: LibraryQueryKeyFactory.all });
		} catch {
			markedFull = previous;
			toastStore.show({ message: "Couldn't update this album", type: 'error' });
		} finally {
			savingFull = false;
		}
	}
</script>

<div
	class="card bg-base-100 w-full shadow-sm shrink-0 group relative transition-all hover:scale-105 hover:glow-primary"
>
	<a {href} class="block h-full" aria-label="Open {album.title}">
		<figure class="aspect-square overflow-hidden relative">
			<AlbumImage
				mbid={album.id}
				source="local"
				available={album.cover_available}
				alt={album.title}
				size="full"
				requestSize={250}
				rounded="none"
				className="w-full h-full"
			/>
			<div class="absolute top-2 right-2 z-10">
				<LibraryFormatBadge format={album.format} />
			</div>
			{#if album.album_identity_state === 'local_only'}
				<LocalIdentityBadge
					state={album.album_identity_state}
					subject="album"
					compact
					className="absolute left-2 top-2 z-10"
				/>
			{/if}
		</figure>

		<div class="card-body p-3">
			<h2 class="card-title text-sm line-clamp-2 min-h-[2.5rem]">{album.title}</h2>
			<p class="text-xs opacity-70 line-clamp-1">
				{#if album.year}{album.year}{:else}Unknown{/if}
				{#if album.artist_name}
					<span class="opacity-50 mx-1">•</span>{album.artist_name}
				{/if}
			</p>
			<p class="text-[11px] opacity-50">
				{album.track_count}
				{album.track_count === 1 ? 'track' : 'tracks'}
			</p>
		</div>
	</a>
	<label
		class="absolute bottom-3 left-3 z-20 flex items-center gap-1 rounded-md bg-base-100/90 px-1.5 py-1 text-[11px] shadow-sm"
	>
		<input
			type="checkbox"
			class="checkbox checkbox-xs checkbox-primary"
			checked={markedFull}
			disabled={savingFull}
			aria-label="Mark {album.title} as full"
			onchange={toggleFull}
		/>
		Full
	</label>
</div>
