import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Join from './pages/Join'
import Psw from './pages/Psw'
import Nurse from './pages/Nurse'
import ResidentProfile from './pages/ResidentProfile'
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/join" element={<Join />} />
        <Route path="/psw" element={<Psw />} />
        <Route path="/nurse" element={<Nurse />} />
        <Route path="/nurse/residents/:residentId" element={<ResidentProfile />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
