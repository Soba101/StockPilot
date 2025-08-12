'use client';

import { redirect } from 'next/navigation';

// Root: always send to /login. (If already logged in, auth layout or /login page can redirect onward.)
export default function HomePage() {
  redirect('/login');
}