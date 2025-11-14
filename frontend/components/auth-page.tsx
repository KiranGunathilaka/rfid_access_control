"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { User, Lock, AlertCircle, CheckCircle, Eye, EyeOff, Link } from "lucide-react"
import { apiUrls } from "@/lib/api"

interface AuthResponse {
  token?: string
  message?: string
  admin?: {
    id: string
    username: string
  }
}

export default function AuthPage() {
  const [loginData, setLoginData] = useState({ username: "", password: "" })
  const [registerData, setRegisterData] = useState({ username: "", password: "" })
  const [loginLoading, setLoginLoading] = useState(false)
  const [registerLoading, setRegisterLoading] = useState(false)
  const [loginError, setLoginError] = useState("")
  const [registerError, setRegisterError] = useState("")
  const [registerSuccess, setRegisterSuccess] = useState("")
  const [showLoginPassword, setShowLoginPassword] = useState(false)
  const [showRegisterPassword, setShowRegisterPassword] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoginLoading(true)
    setLoginError("")

    try {
      const response = await fetch(apiUrls.login(), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(loginData),
      })

      const data: AuthResponse = await response.json()

      if (response.ok && data.token) {
        localStorage.setItem("adminToken", data.token)
        window.location.href = "/dashboard"
      } else {
        setLoginError(data.message || "Login failed")
      }
    } catch (error) {
      setLoginError("Network error. Please check if the server is running.")
    } finally {
      setLoginLoading(false)
    }
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setRegisterLoading(true)
    setRegisterError("")
    setRegisterSuccess("")

    try {
      const response = await fetch(apiUrls.register(), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(registerData),
      })

      const data: AuthResponse = await response.json()

      if (response.ok) {
        setRegisterSuccess(`Admin "${data.admin?.username}" created successfully!`)
        setRegisterData({ username: "", password: "" })
      } else {
        setRegisterError(data.message || "Registration failed")
      }
    } catch (error) {
      setRegisterError("Network error. Please check if the server is running.")
    } finally {
      setRegisterLoading(false)
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden"
      style={{
        backgroundImage: "url('/images/login-bg.webp')",
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundRepeat: "no-repeat",
      }}
    >
      {/* Dark overlay for better contrast */}
      <div className="absolute inset-0 bg-black/30 backdrop-blur-[2px]"></div>

      {/* Subtle animated overlay elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-20 left-20 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-20 right-20 w-40 h-40 bg-purple-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute top-1/2 left-1/3 w-24 h-24 bg-cyan-500/10 rounded-full blur-3xl animate-pulse delay-500"></div>
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-6">
            <div className="relative">
              <img src="/images/logo.webp" alt="SPOTSEEKER.LK Logo" className="h-16 w-auto mr-3 drop-shadow-2xl" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white drop-shadow-2xl">ACCESS PRO</h1>
              <p className="text-lg font-semibold text-cyan-300 drop-shadow-lg">Admin Portal</p>
            </div>
          </div>
          <p className="text-gray-200 text-lg drop-shadow-lg">Admin Portal - Secure Access Control</p>
        </div>

        {/* Auth Card */}
        <Card className="shadow-2xl border-0 bg-white/95 backdrop-blur-md">
          <CardHeader className="space-y-1 pb-6 bg-gradient-to-r from-slate-50 to-blue-50/50 rounded-t-lg">
            <CardTitle className="text-2xl text-center text-gray-900 font-bold">Admin Access</CardTitle>
            <CardDescription className="text-center text-gray-600">
              Secure authentication for system administrators
            </CardDescription>
          </CardHeader>
          <CardContent className="p-6">
            <Tabs defaultValue="login" className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-6 bg-slate-100/80 p-1 rounded-lg">
                <TabsTrigger
                  value="login"
                  className="text-gray-700 data-[state=active]:bg-slate-800 data-[state=active]:text-white data-[state=active]:shadow-md transition-all duration-200"
                >
                  Sign In
                </TabsTrigger>
                <TabsTrigger
                  value="register"
                  className="text-gray-700 data-[state=active]:bg-slate-800 data-[state=active]:text-white data-[state=active]:shadow-md transition-all duration-200"
                >
                  Register
                </TabsTrigger>
              </TabsList>

              {/* Login Tab */}
              <TabsContent value="login" className="space-y-4">
                <form onSubmit={handleLogin} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="login-username" className="text-gray-700 font-medium">
                      Username
                    </Label>
                    <div className="relative">
                      <User className="absolute left-3 top-3 h-4 w-4 text-slate-600" />
                      <Input
                        id="login-username"
                        type="text"
                        placeholder="Enter your username"
                        className="pl-10 bg-white border-slate-300 text-gray-900 placeholder-gray-500 focus:border-slate-600 focus:ring-slate-600/20 transition-colors"
                        value={loginData.username}
                        onChange={(e) => setLoginData({ ...loginData, username: e.target.value })}
                        required
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="login-password" className="text-gray-700 font-medium">
                      Password
                    </Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-3 h-4 w-4 text-slate-600" />
                      <Input
                        id="login-password"
                        type={showLoginPassword ? "text" : "password"}
                        placeholder="Enter your password"
                        className="pl-10 pr-10 bg-white border-slate-300 text-gray-900 placeholder-gray-500 focus:border-slate-600 focus:ring-slate-600/20 transition-colors"
                        value={loginData.password}
                        onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                        required
                      />
                      <button
                        type="button"
                        className="absolute right-3 top-3 text-slate-600 hover:text-slate-700 transition-colors"
                        onClick={() => setShowLoginPassword(!showLoginPassword)}
                      >
                        {showLoginPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>

                  {loginError && (
                    <Alert variant="destructive" className="bg-red-50 border-red-300 animate-in slide-in-from-top-2">
                      <AlertCircle className="h-4 w-4 text-red-600" />
                      <AlertDescription className="text-red-800">{loginError}</AlertDescription>
                    </Alert>
                  )}
                  <Button
                    type="submit"
                    className="w-full bg-gradient-to-r from-slate-700 to-slate-800 hover:from-slate-800 hover:to-slate-900 text-white shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-[1.02]"
                    disabled={loginLoading}
                  >
                    {loginLoading ? (
                      <div className="flex items-center">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Signing In...
                      </div>
                    ) : (
                      "Sign In"
                    )}
                  </Button>
                </form>
              </TabsContent>

              {/* Register Tab */}
              <TabsContent value="register" className="space-y-4">
                <form onSubmit={handleRegister} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="register-username" className="text-gray-700 font-medium">
                      Username
                    </Label>
                    <div className="relative">
                      <User className="absolute left-3 top-3 h-4 w-4 text-slate-600" />
                      <Input
                        id="register-username"
                        type="text"
                        placeholder="Choose a username"
                        className="pl-10 bg-white border-slate-300 text-gray-900 placeholder-gray-500 focus:border-slate-600 focus:ring-slate-600/20 transition-colors"
                        value={registerData.username}
                        onChange={(e) => setRegisterData({ ...registerData, username: e.target.value })}
                        required
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="register-password" className="text-gray-700 font-medium">
                      Password
                    </Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-3 h-4 w-4 text-slate-600" />
                      <Input
                        id="register-password"
                        type={showRegisterPassword ? "text" : "password"}
                        placeholder="Create a password"
                        className="pl-10 pr-10 bg-white border-slate-300 text-gray-900 placeholder-gray-500 focus:border-slate-600 focus:ring-slate-600/20 transition-colors"
                        value={registerData.password}
                        onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                        required
                      />
                      <button
                        type="button"
                        className="absolute right-3 top-3 text-slate-600 hover:text-slate-700 transition-colors"
                        onClick={() => setShowRegisterPassword(!showRegisterPassword)}
                      >
                        {showRegisterPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>

                  {registerError && (
                    <Alert variant="destructive" className="bg-red-50 border-red-300 animate-in slide-in-from-top-2">
                      <AlertCircle className="h-4 w-4 text-red-600" />
                      <AlertDescription className="text-red-800">{registerError}</AlertDescription>
                    </Alert>
                  )}

                  {registerSuccess && (
                    <Alert className="border-green-300 bg-green-50 animate-in slide-in-from-top-2">
                      <CheckCircle className="h-4 w-4 text-green-600" />
                      <AlertDescription className="text-green-800">{registerSuccess}</AlertDescription>
                    </Alert>
                  )}

                  <Button
                    type="submit"
                    className="w-full bg-gradient-to-r from-slate-700 to-slate-800 hover:from-slate-800 hover:to-slate-900 text-white shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-[1.02]"
                    disabled={registerLoading}
                  >
                    {registerLoading ? (
                      <div className="flex items-center">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Creating Account...
                      </div>
                    ) : (
                      "Create Admin Account"
                    )}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="text-center mt-8 text-gray-200">
          <p className="drop-shadow-lg">© 2024 SPOTSEEKER ACCESS PRO. All rights reserved.</p>
          <p className="mt-1 text-sm drop-shadow-lg">Secure admin portal for access control management</p>
        </div>
      </div>
    </div>
  )
}
