// Phone utilities for Israeli numbers
// - localizeILPhone: convert +972/972/00972 to local format starting with 0, remove common separators
// - formatILPhoneDisplay: pretty-print for UI (e.g., 054-397-1675)

export function localizeILPhone(raw?: string | null): string | null {
  if (!raw) return null;
  // trim and remove common separators for consistency
  const cleaned = raw.trim().replace(/[()\s-]/g, '');
  // Already local (starts with 0) -> leave as-is
  if (/^0\d+$/.test(cleaned)) return cleaned;
  // Replace leading variants of country code with a single leading 0
  if (/^\+972/.test(cleaned)) return cleaned.replace(/^\+972/, '0');
  if (/^00972/.test(cleaned)) return cleaned.replace(/^00972/, '0');
  if (/^972/.test(cleaned)) return cleaned.replace(/^972/, '0');
  // Fallback to cleaned original
  return cleaned;
}

// Format Israeli numbers for display
// Rules:
// - Mobile (05x + 7 digits): 054-397-1675 => 3-3-4
// - Classic landline (02/03/04/08/09 + 7): 03-1234567 => 2-7
// - VoIP prefixes (072/073/074/076/077/079 + 7): 072-1234567 => 3-7
// - Otherwise: fallbacks (len 10 => 3-3-4, len 9 => 2-7)
export function formatILPhoneDisplay(raw?: string | null): string | null {
  const localized = localizeILPhone(raw);
  if (!localized) return null;
  const digits = localized.replace(/\D/g, '');

  // Mobile: 05x-xxx-xxxx
  if (/^05\d{8}$/.test(digits)) {
    return `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6)}`;
  }

  // Landline major areas: 02/03/04/08/09 => 2-7
  if (/^0[23489]\d{7}$/.test(digits)) {
    return `${digits.slice(0, 2)}-${digits.slice(2)}`;
  }

  // VoIP prefixes: 072/073/074/076/077/079 => 3-7
  if (/^0(?:72|73|74|76|77|79)\d{7}$/.test(digits)) {
    return `${digits.slice(0, 3)}-${digits.slice(3)}`;
  }

  // Generic fallbacks
  if (/^\d{10}$/.test(digits)) {
    return `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6)}`;
  }
  if (/^\d{9}$/.test(digits)) {
    return `${digits.slice(0, 2)}-${digits.slice(2)}`;
  }

  // Unknown shape -> return as-is
  return digits;
}
