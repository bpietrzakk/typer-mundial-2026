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
