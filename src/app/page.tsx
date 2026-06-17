import { redirect } from 'next/navigation'

export default function Home() {
  // Redirect to the main static site
  redirect('/index.html')
}
