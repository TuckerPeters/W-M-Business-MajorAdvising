const STORAGE_KEY = 'wm-advisor-accounts';

export interface AdvisorAccount {
  email: string;
  name: string;
  status: 'pending' | 'approved';
  createdAt: string;
}

function getAccounts(): AdvisorAccount[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveAccounts(accounts: AdvisorAccount[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(accounts));
}

export function registerAdvisorAccount(email: string, name: string): AdvisorAccount {
  const accounts = getAccounts();
  const existing = accounts.find(a => a.email.toLowerCase() === email.toLowerCase());
  if (existing) return existing;
  const account: AdvisorAccount = {
    email,
    name,
    status: 'pending',
    createdAt: new Date().toISOString(),
  };
  accounts.push(account);
  saveAccounts(accounts);
  return account;
}

export function getAdvisorAccountStatus(email: string): AdvisorAccount | null {
  return getAccounts().find(a => a.email.toLowerCase() === email.toLowerCase()) || null;
}

export function approveAdvisorAccount(email: string): boolean {
  const accounts = getAccounts();
  const account = accounts.find(a => a.email.toLowerCase() === email.toLowerCase());
  if (!account) return false;
  account.status = 'approved';
  saveAccounts(accounts);
  return true;
}

export function removeAdvisorAccount(email: string): boolean {
  const accounts = getAccounts();
  const filtered = accounts.filter(a => a.email.toLowerCase() !== email.toLowerCase());
  if (filtered.length === accounts.length) return false;
  saveAccounts(filtered);
  return true;
}

export function getPendingAdvisors(): AdvisorAccount[] {
  return getAccounts().filter(a => a.status === 'pending');
}

export function getApprovedAdvisors(): AdvisorAccount[] {
  return getAccounts().filter(a => a.status === 'approved');
}

export function getAllAdvisorAccounts(): AdvisorAccount[] {
  return getAccounts();
}
