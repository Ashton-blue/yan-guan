import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import TeamCreate from './pages/TeamCreate';
import Dashboard from './pages/Dashboard';
import Members from './pages/Members';
import ChangePassword from './pages/ChangePassword';
import Layout from './components/Layout';
import PrivateRoute from './components/PrivateRoute';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/change-password" element={
        <PrivateRoute><ChangePassword /></PrivateRoute>
      } />
      <Route path="/team/create" element={
        <PrivateRoute>
          <Layout><TeamCreate /></Layout>
        </PrivateRoute>
      } />
      <Route path="/" element={
        <PrivateRoute>
          <Layout><Dashboard /></Layout>
        </PrivateRoute>
      } />
      <Route path="/members" element={
        <PrivateRoute>
          <Layout><Members /></Layout>
        </PrivateRoute>
      } />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
