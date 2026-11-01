// copy a text for the group chat and open the system share sheet when there is one.
// returns true when the text landed in the clipboard
export async function copyAndShare(text, title = 'czutka') {
  let copied = false;
  try {
    await navigator.clipboard.writeText(text);
    copied = true;
  } catch {
    // clipboard blocked (http, old browser) — the share sheet may still work
  }
  if (navigator.share) {
    try {
      await navigator.share({ title, text });
    } catch {
      // user closed the share sheet
    }
  }
  return copied;
}

// invite link of a league — /join/CODE also opens the league for a member
export const inviteUrl = (joinCode) => `${window.location.origin}/join/${joinCode}`;

// share a PNG: system share sheet with the file when the browser can (phones),
// otherwise copy it to the clipboard as an image (best effort) and download it.
// returns 'shared' | 'cancelled' | 'copied' | 'downloaded'
export async function shareImage(blob, filename, text) {
  const file = new File([blob], filename, { type: 'image/png' });
  if (navigator.canShare?.({ files: [file] })) {
    try {
      await navigator.share({ files: [file], title: 'czutka', text });
      return 'shared';
    } catch (err) {
      if (err?.name === 'AbortError') return 'cancelled';
      // share failed for another reason — fall back to download
    }
  }
  let copied = false;
  try {
    if (window.ClipboardItem && navigator.clipboard?.write) {
      await navigator.clipboard.write([new window.ClipboardItem({ 'image/png': blob })]);
      copied = true;
    }
  } catch {
    // clipboard images blocked (firefox, http) — the download is enough
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return copied ? 'copied' : 'downloaded';
}
