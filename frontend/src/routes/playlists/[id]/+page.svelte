<script lang="ts">
	import { goto } from '$app/navigation';
	import { onDestroy, untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import {
		deletePlaylist,
		linkPlaylistTrackToLibrary,
		matchPlaylistLibrary,
		resolvePlaylistSources,
		requestMissingTracks,
		isRedactedPlaylist,
		type PlaylistDetail,
		type PlaylistDetailItem,
		type PlaylistLibraryMatchResult,
		type RedactedPlaylist
	} from '$lib/api/playlists';
	import { playlistTrackToQueueItem } from '$lib/player/queueHelpers';
	import { playerStore } from '$lib/stores/player.svelte';
	import { toastStore } from '$lib/stores/toast';
	import { authStore } from '$lib/stores/authStore.svelte';
	import { getCacheTTL } from '$lib/stores/cacheTtl';
	import { getPlaylistDetailQuery } from '$lib/queries/playlists/PlaylistQuery.svelte';
	import { createSetPlaylistPublicMutation } from '$lib/queries/playlists/PlaylistMutations.svelte';
	import { invalidateQueriesWithPersister } from '$lib/queries/QueryClient';
	import { PlaylistQueryKeyFactory } from '$lib/queries/playlists/PlaylistQueryKeyFactory';
	import { extractDominantColor, DEFAULT_GRADIENT } from '$lib/utils/colors';
	import { getApiUrl } from '$lib/api/api-utils';
	import { Music, Lock, Download, Loader2 } from 'lucide-svelte';
	import BackButton from '$lib/components/BackButton.svelte';
	import HeroBackdrop from '$lib/components/HeroBackdrop.svelte';
	import type { PageData } from './$types';
	import PlaylistHeader from './PlaylistHeader.svelte';
	import PlaylistTrackList from './PlaylistTrackList.svelte';
	import DeletePlaylistModal from './DeletePlaylistModal.svelte';

	let { data }: { data: PageData } = $props();

	const detailQuery = getPlaylistDetailQuery(
		() => data.playlistId,
		() => true
	);
	const shareMutation = createSetPlaylistPublicMutation();

	// A local mutable copy of the (full) playlist so child components can keep
	// applying optimistic updates; redaction/loading/error leave it null.
	let playlist = $state<PlaylistDetail | null>(null);
	let deleting = $state(false);

	let deleteModal = $state<ReturnType<typeof DeletePlaylistModal> | null>(null);
	let trackList = $state<ReturnType<typeof PlaylistTrackList> | null>(null);
	let header = $state<ReturnType<typeof PlaylistHeader> | null>(null);

	let redacted = $derived(
		detailQuery.data && isRedactedPlaylist(detailQuery.data)
			? (detailQuery.data as RedactedPlaylist)
			: null
	);
	let loading = $derived(detailQuery.isLoading);
	let loadError = $derived.by(() => {
		if (!detailQuery.isError) return null;
		const msg = detailQuery.error instanceof Error ? detailQuery.error.message : '';
		return /404|not found/i.test(msg) ? 'Playlist not found' : "Couldn't load this playlist";
	});

	let isOwner = $derived(playlist?.is_owner ?? false);
	let canDelete = $derived((playlist?.is_owner ?? false) || authStore.isAdmin);

	let missingAlbumCount = $derived.by(() => {
		if (!playlist) return 0;
		const seen = new SvelteSet<string>();
		for (const t of playlist.tracks) {
			if (t.album_id && (!t.available_sources || t.available_sources.length === 0)) {
				seen.add(t.album_id);
			}
		}
		return seen.size;
	});

	let requesting = $state(false);
	let matchingLibrary = $state(false);
	let libraryMatch = $state<PlaylistLibraryMatchResult | null>(null);
	let matchedPlaylistIds = new SvelteSet<string>();
	let linkingTrackIds = new SvelteSet<string>();

	async function handleRequestMissing() {
		if (requesting || !playlist) return;
		requesting = true;
		try {
			const result = await requestMissingTracks(playlist.id);
			toastStore.show({ message: result.message, type: 'success' });
		} catch {
			toastStore.show({ message: "Couldn't submit requests", type: 'error' });
		} finally {
			requesting = false;
		}
	}

	async function matchPlaylistTracks(playlistId: string) {
		if (matchingLibrary || matchedPlaylistIds.has(playlistId)) return;
		matchingLibrary = true;
		try {
			const result = await matchPlaylistLibrary(playlistId);
			matchedPlaylistIds.add(playlistId);
			if (playlist?.id !== playlistId) return;
			libraryMatch = result;
			for (const match of result.tracks) {
				if (match.status !== 'matched' || !match.candidate) continue;
				const track = playlist.tracks.find((item) => item.id === match.track_id);
				if (!track) continue;
				track.source_type = 'local';
				track.track_source_id = match.candidate.track_file_id;
				track.library_file_id = match.candidate.track_file_id;
				track.available_sources = ['local'];
				track.format = match.candidate.format || track.format;
				track.cover_url = match.candidate.cover_url || track.cover_url;
			}
		} catch {
			toastStore.show({ message: "Couldn't match playlist tracks to your library", type: 'error' });
		} finally {
			matchingLibrary = false;
		}
	}

	async function acceptLibraryMatch(trackId: string, trackFileId: string) {
		if (!playlist || !libraryMatch || linkingTrackIds.has(trackId)) return;
		const selectedMatch = libraryMatch.tracks.find((match) => match.track_id === trackId);
		linkingTrackIds.add(trackId);
		try {
			const updated = await linkPlaylistTrackToLibrary(playlist.id, trackId, trackFileId);
			const track = playlist.tracks.find((item) => item.id === trackId);
			if (track) {
				track.source_type = updated.source_type;
				track.track_source_id = updated.track_source_id;
				track.library_file_id = updated.library_file_id;
				track.available_sources = updated.available_sources;
				track.format = updated.format || selectedMatch?.candidate?.format || track.format;
				track.cover_url =
					updated.cover_url || selectedMatch?.candidate?.cover_url || track.cover_url;
			}
			libraryMatch = {
				...libraryMatch,
				matched: libraryMatch.matched + 1,
				close: Math.max(0, libraryMatch.close - 1),
				tracks: libraryMatch.tracks.map((match) =>
					match.track_id === trackId ? { ...match, status: 'matched' } : match
				)
			};
			toastStore.show({ message: 'Linked track to your library', type: 'success' });
		} catch {
			toastStore.show({ message: "Couldn't link that library match", type: 'error' });
		} finally {
			linkingTrackIds.delete(trackId);
		}
	}

	// Source-resolution cache is namespaced per user so two accounts on a shared
	// browser never read each other's resolved sources (AMU-5).
	const SOURCES_CACHE_PREFIX = 'droppedneedle_playlist_sources_';
	function sourcesCacheKey(playlistId: string): string {
		return `${SOURCES_CACHE_PREFIX}${authStore.user?.id ?? 'anon'}_${playlistId}`;
	}

	function getSourcesFromCache(playlistId: string): Record<string, string[]> | null {
		try {
			const key = sourcesCacheKey(playlistId);
			const raw = localStorage.getItem(key);
			if (!raw) return null;
			const cached = JSON.parse(raw) as { ts: number; data: Record<string, string[]> };
			const ttl = getCacheTTL('playlistSources');
			if (Date.now() - cached.ts > ttl) {
				localStorage.removeItem(key);
				return null;
			}
			return cached.data;
		} catch {
			return null;
		}
	}

	function setSourcesCache(playlistId: string, sources: Record<string, string[]>) {
		try {
			localStorage.setItem(
				sourcesCacheKey(playlistId),
				JSON.stringify({ ts: Date.now(), data: sources })
			);
		} catch {
			/* storage full - non-critical */
		}
	}

	function invalidateSourcesCache(playlistId: string) {
		try {
			localStorage.removeItem(sourcesCacheKey(playlistId));
		} catch {
			/* ignore */
		}
	}

	function applySourcesMap(sources: Record<string, string[]>) {
		if (!playlist) return;
		for (const track of playlist.tracks) {
			const resolved = sources[track.id];
			if (resolved && resolved.length > 0) {
				track.available_sources = resolved;
			}
		}
	}

	async function resolveAndCacheSources(playlistId: string) {
		const cached = getSourcesFromCache(playlistId);
		if (cached) {
			applySourcesMap(cached);
			return;
		}
		try {
			const sources = await resolvePlaylistSources(playlistId);
			if (playlist && playlist.id === playlistId) {
				applySourcesMap(sources);
				setSourcesCache(playlistId, sources);
			}
		} catch {
			// non-critical - tracks keep their stored available_sources
		}
	}

	let lastSyncedData: PlaylistDetailItem | undefined;
	$effect(() => {
		const d = detailQuery.data;
		if (d === lastSyncedData) return;
		lastSyncedData = d;
		untrack(() => {
			trackList?.clearReorderState();
			header?.cleanupPreview();
			if (d && !isRedactedPlaylist(d)) {
				// Clone so optimistic child mutations never touch the query cache.
				playlist = { ...d, tracks: d.tracks.map((t) => ({ ...t })) };
				void resolveAndCacheSources(d.id);
				if (d.source_ref?.startsWith('exportify:') && d.is_owner) {
					void matchPlaylistTracks(d.id);
				}
			} else {
				playlist = null;
			}
		});
	});

	function playAll() {
		if (!playlist || playlist.tracks.length === 0) return;
		const items = playlist.tracks
			.map(playlistTrackToQueueItem)
			.filter((item): item is NonNullable<typeof item> => item !== null);
		if (items.length === 0) {
			toastStore.show({ message: 'Nothing here can be played right now', type: 'info' });
			return;
		}
		playerStore.playQueue(items, 0, false);
	}

	function shuffleAll() {
		if (!playlist || playlist.tracks.length < 2) return;
		const items = playlist.tracks
			.map(playlistTrackToQueueItem)
			.filter((item): item is NonNullable<typeof item> => item !== null);
		if (items.length === 0) {
			toastStore.show({ message: 'Nothing here can be played right now', type: 'info' });
			return;
		}
		playerStore.playQueue(items, 0, true);
	}

	function playFromTrack(index: number) {
		if (!playlist || playlist.tracks.length === 0) return;
		const items = playlist.tracks
			.map(playlistTrackToQueueItem)
			.filter((item): item is NonNullable<typeof item> => item !== null);
		if (items.length === 0) {
			toastStore.show({ message: 'Nothing here can be played right now', type: 'info' });
			return;
		}
		const startIndex = Math.min(index, items.length - 1);
		playerStore.playQueue(items, startIndex, false);
	}

	function handleSourceChange() {
		if (playlist) invalidateSourcesCache(playlist.id);
	}

	function handlePlaylistUpdate(updatedPlaylist: PlaylistDetail) {
		playlist = updatedPlaylist;
	}

	async function handleShare(isPublic: boolean) {
		if (!playlist || shareMutation.isPending) return;
		try {
			const updated = await shareMutation.mutateAsync({ id: playlist.id, isPublic });
			playlist = { ...playlist, is_public: updated.is_public };
			toastStore.show({
				message: updated.is_public ? 'Playlist is now public' : 'Playlist is now private',
				type: 'success'
			});
		} catch {
			toastStore.show({ message: "Couldn't update sharing", type: 'error' });
		}
	}

	async function confirmDelete() {
		if (!playlist || deleting) return;
		deleting = true;
		try {
			await deletePlaylist(playlist.id);
			await invalidateQueriesWithPersister({
				queryKey: PlaylistQueryKeyFactory.list(authStore.user?.id)
			});
			toastStore.show({ message: 'Playlist deleted', type: 'success' });
			await goto('/playlists');
		} catch {
			toastStore.show({ message: "Couldn't delete the playlist", type: 'error' });
		} finally {
			deleting = false;
		}
	}

	let heroGradient = $state(DEFAULT_GRADIENT);

	let heroBgUrl = $derived.by(() => {
		if (!playlist) return null;
		if (playlist.custom_cover_url) return getApiUrl(playlist.custom_cover_url);
		if (playlist.cover_urls.length > 0) return getApiUrl(playlist.cover_urls[0]);
		return null;
	});

	$effect(() => {
		const url = heroBgUrl;
		if (url) {
			extractDominantColor(url).then((gradient) => (heroGradient = gradient));
		} else {
			heroGradient = DEFAULT_GRADIENT;
		}
	});

	onDestroy(() => {
		trackList?.clearReorderState();
		header?.cleanupPreview();
	});
</script>

<svelte:head>
	<title>{playlist?.name ?? 'Playlist'} - DroppedNeedle</title>
</svelte:head>

<div class="w-full px-2 sm:px-4 lg:px-8 py-4 sm:py-8 max-w-7xl mx-auto">
	{#if loading}
		<div class="space-y-6 sm:space-y-8">
			<div class="skeleton h-10 w-10 rounded-full"></div>
			<div class="flex flex-col lg:flex-row gap-6 lg:gap-8">
				<div class="skeleton w-full lg:w-64 xl:w-80 aspect-square rounded-box shrink-0"></div>
				<div class="flex-1 flex flex-col justify-end space-y-4">
					<div class="skeleton h-4 w-20"></div>
					<div class="skeleton h-12 w-3/4"></div>
					<div class="skeleton h-6 w-1/2"></div>
					<div class="flex gap-4 mt-6">
						<div class="skeleton h-12 w-32"></div>
						<div class="skeleton h-12 w-32"></div>
					</div>
				</div>
			</div>
			<div class="space-y-2">
				{#each Array(4) as _, i (`loading-track-${i}`)}
					<div class="skeleton h-14 w-full"></div>
				{/each}
			</div>
		</div>
	{:else if loadError}
		<div class="flex flex-col items-center justify-center py-20 gap-4 text-center">
			<Music class="h-16 w-16 text-base-content/20" />
			<h2 class="text-lg font-semibold text-base-content/80">Couldn't load this playlist</h2>
			<p class="text-sm text-base-content/60">{loadError}</p>
			<div class="flex items-center gap-2">
				<button class="btn btn-sm btn-accent" onclick={() => void detailQuery.refetch()}>
					Retry
				</button>
				<BackButton fallback="/playlists" />
			</div>
		</div>
	{:else if redacted}
		<div class="flex flex-col items-center justify-center py-20 gap-4 text-center">
			<div class="flex items-center justify-center rounded-full bg-base-200 p-5">
				<Lock class="h-12 w-12 text-base-content/30" />
			</div>
			<h2 class="text-lg font-semibold italic text-base-content/70">Private playlist</h2>
			<p class="text-sm text-base-content/60">
				{redacted.track_count} track{redacted.track_count === 1 ? '' : 's'}{redacted.owner_name
					? ` · owned by ${redacted.owner_name}`
					: ''}
			</p>
			<BackButton fallback="/playlists" />
		</div>
	{:else if !playlist}
		<div class="flex flex-col items-center justify-center py-20 gap-4">
			<Music class="h-16 w-16 text-base-content/20" />
			<h2 class="text-lg font-semibold text-base-content/60">Playlist not found</h2>
			<BackButton fallback="/playlists" />
		</div>
	{:else}
		<div class="space-y-6 sm:space-y-8">
			<div
				class="group relative rounded-box playlist-hero"
				style="--hero-glow-color: var(--brand-hero);"
			>
				<div
					class="absolute inset-0 bg-linear-to-b {heroGradient} transition-all duration-1000 rounded-box"
				></div>
				<HeroBackdrop
					imageUrl={heroBgUrl}
					opacity={0.15}
					hoverOpacity={0.2}
					blur={3}
					hoverBlur={2}
					position="full"
				/>
				<div
					class="absolute inset-0 bg-linear-to-b from-transparent via-base-100/50 to-base-100/80 rounded-box pointer-events-none"
				></div>

				<div class="relative z-10 p-4 sm:p-6 lg:p-8">
					<div class="mb-4">
						<BackButton fallback="/playlists" />
					</div>

					<PlaylistHeader
						bind:this={header}
						{playlist}
						canEdit={isOwner}
						{canDelete}
						sharePending={shareMutation.isPending}
						onplayall={playAll}
						onshuffleall={shuffleAll}
						ondeleteclick={() => deleteModal?.showModal()}
						onplaylistupdate={handlePlaylistUpdate}
						onshare={handleShare}
					/>
				</div>
			</div>

			{#if isOwner && playlist.source_ref?.startsWith('exportify:')}
				<section class="space-y-3 border-y border-base-300/50 py-4" aria-live="polite">
					<div class="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
						{#if matchingLibrary && !libraryMatch}
							<span class="inline-flex items-center gap-2 text-base-content/65">
								<Loader2 class="h-4 w-4 animate-spin" /> Checking your library…
							</span>
						{:else if libraryMatch}
							<span class="font-medium text-success">{libraryMatch.matched} matched</span>
							<span class="font-medium text-warning">{libraryMatch.close} close matches</span>
							<span class="text-base-content/65">{libraryMatch.missing} not found</span>
						{:else}
							<span class="text-base-content/65">Library matching has not run</span>
						{/if}
					</div>
					{#if libraryMatch?.tracks.some((match) => match.status === 'close' && match.candidate)}
						<details>
							<summary class="cursor-pointer text-sm font-semibold">Review close matches</summary>
							<ul class="mt-2 divide-y divide-base-300/40 text-sm">
								{#each libraryMatch.tracks.filter((match) => match.status === 'close' && match.candidate) as match (match.track_id)}
									{@const sourceTrack = playlist.tracks.find(
										(track) => track.id === match.track_id
									)}
									<li class="grid gap-x-3 gap-y-2 py-2 sm:grid-cols-[1fr_1fr_auto] sm:items-center">
										<span class="min-w-0 truncate text-base-content/65"
											>{sourceTrack?.artist_name} · {sourceTrack?.track_name}</span
										>
										<span class="min-w-0 truncate"
											>{match.candidate?.artist_name} · {match.candidate?.title}
											<span class="text-xs text-base-content/50"
												>({Math.round((match.candidate?.score ?? 0) * 100)}%)</span
											></span
										>
										<button
											class="btn btn-xs"
											onclick={() =>
												void acceptLibraryMatch(match.track_id, match.candidate!.track_file_id)}
											disabled={linkingTrackIds.has(match.track_id)}
										>
											{#if linkingTrackIds.has(match.track_id)}<Loader2
													class="h-3 w-3 animate-spin"
												/>{:else}Use this match{/if}
										</button>
									</li>
								{/each}
							</ul>
						</details>
					{/if}
					{#if libraryMatch?.missing}
						<details>
							<summary class="cursor-pointer text-sm font-semibold"
								>Not found in your library</summary
							>
							<ul class="mt-2 max-h-64 divide-y divide-base-300/40 overflow-y-auto text-sm">
								{#each libraryMatch.tracks.filter((match) => match.status === 'missing') as match (match.track_id)}
									{@const sourceTrack = playlist.tracks.find(
										(track) => track.id === match.track_id
									)}
									<li class="py-2 text-base-content/70">
										{sourceTrack?.artist_name} · {sourceTrack?.track_name}
									</li>
								{/each}
							</ul>
						</details>
					{/if}
				</section>
			{/if}

			{#if isOwner && (missingAlbumCount > 0 || (libraryMatch && libraryMatch.missing + libraryMatch.close > 0))}
				<div
					class="flex items-center gap-3 rounded-xl border border-base-300/40 bg-base-200/40 px-4 py-3"
				>
					<Download class="h-4 w-4 shrink-0 text-base-content/50" />
					<p class="flex-1 text-sm text-base-content/70">
						{#if playlist.source_ref?.startsWith('exportify:')}
							{(libraryMatch?.missing ?? 0) + (libraryMatch?.close ?? 0)} songs still need a match
						{:else}
							{missingAlbumCount}
							{missingAlbumCount === 1 ? 'album' : 'albums'} not in your library
						{/if}
					</p>
					<button
						class="btn btn-accent btn-sm"
						onclick={() => void handleRequestMissing()}
						disabled={requesting || missingAlbumCount === 0}
					>
						{#if requesting}
							<Loader2 class="h-3.5 w-3.5 animate-spin" />
						{:else}
							<Download class="h-3.5 w-3.5" />
						{/if}
						{playlist.source_ref?.startsWith('exportify:')
							? 'Look for them all'
							: `Request ${missingAlbumCount === 1 ? 'album' : missingAlbumCount + ' albums'}`}
					</button>
					{#if playlist.source_ref?.startsWith('exportify:') && missingAlbumCount === 0}
						<p class="basis-full text-xs text-base-content/55">
							No album match is available to search for these tracks yet.
						</p>
					{/if}
				</div>
			{/if}

			<PlaylistTrackList
				bind:this={trackList}
				{playlist}
				readonly={!isOwner}
				ontrackchange={() => {}}
				onsourcechange={handleSourceChange}
				onplaytrack={playFromTrack}
			/>
		</div>

		<DeletePlaylistModal
			bind:this={deleteModal}
			playlistName={playlist.name}
			{deleting}
			onconfirm={() => void confirmDelete()}
		/>
	{/if}
</div>
