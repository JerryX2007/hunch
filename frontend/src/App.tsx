import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import RequireNurse from './components/RequireNurse'
import Home from './pages/Home'
import Join from './pages/Join'
import Login from './pages/Login'
import Psw from './pages/Psw'
import Nurse from './pages/Nurse'
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/join" element={<Join />} />
        {/* No sign-in for PSWs: the note screen only sees resident names. */}
        <Route path="/psw" element={<Psw />} />
        <Route path="/nurse" element={<RequireNurse><Nurse /></RequireNurse>} />
        {/* Same screen with a resident open, so links and the back button work. */}
        <Route path="/nurse/residents/:residentId" element={<RequireNurse><Nurse /></RequireNurse>} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
