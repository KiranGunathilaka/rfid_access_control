"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Settings, User, AlertCircle, CheckCircle, UserCog, Power, XCircle } from "lucide-react"
import { apiUrls } from "../lib/api"

interface UserUpdateRequest {
  nic?: string
  rfidTag?: string
  status?: "IDLE" | "OUT" | "IN"
  isActive?: boolean
}

export default function UserManagementModal() {
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")

  // Status update form
  const [statusForm, setStatusForm] = useState({
    identifier: "",
    // identifierType: "nic" as "nic" | "rfidTag",
    identifierType: "rfidTag",
    status: "" as "IDLE" | "OUT" | "IN" | "",
  })

  // Active status update form
  const [activeForm, setActiveForm] = useState({
    identifier: "",
    // identifierType: "nic" as "nic" | "rfidTag",
    identifierType: "rfidTag",
    isActive: "" as "true" | "false" | "",
  })

  // RFID update form
  const [rfidForm, setRfidForm] = useState({
    identifier: "",
    // identifierType: "nic" as "nic" | "rfidTag",
    identifierType: "rfidTag",
    newRfidTag: "",
  })

  // User search state
  const [searchResults, setSearchResults] = useState<{
    status: { user: any | null; loading: boolean; error: string }
    active: { user: any | null; loading: boolean; error: string }
    rfid: { user: any | null; loading: boolean; error: string }
  }>({
    status: { user: null, loading: false, error: "" },
    active: { user: null, loading: false, error: "" },
    rfid: { user: null, loading: false, error: "" },
  })

  // Debounce function
  const debounce = (func: Function, wait: number) => {
    let timeout: NodeJS.Timeout
    return function executedFunction(...args: any[]) {
      const later = () => {
        clearTimeout(timeout)
        func(...args)
      }
      clearTimeout(timeout)
      timeout = setTimeout(later, wait)
    }
  }

  // Search user function
  const searchUser = async (identifier: string, formType: "status" | "active" | "rfid") => {
    if (!identifier.trim()) {
      setSearchResults((prev) => ({
        ...prev,
        [formType]: { user: null, loading: false, error: "" },
      }))
      return
    }

    setSearchResults((prev) => ({
      ...prev,
      [formType]: { ...prev[formType], loading: true, error: "" },
    }))

    try {
      const token = localStorage.getItem("adminToken")
      if (!token) {
        throw new Error("No authentication token found")
      }

      const response = await fetch(apiUrls.users(identifier), {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      })

      const result = await response.json()

      if (response.ok && result.success && result.data.length > 0) {
        // Find exact match first, then partial match
        const exactMatch = result.data.find((user: any) => user.nic === identifier || user.rfidTag === identifier)
        const foundUser = exactMatch || result.data[0]

        setSearchResults((prev) => ({
          ...prev,
          [formType]: { user: foundUser, loading: false, error: "" },
        }))
      } else {
        setSearchResults((prev) => ({
          ...prev,
          [formType]: { user: null, loading: false, error: "User not found" },
        }))
      }
    } catch (error) {
      setSearchResults((prev) => ({
        ...prev,
        [formType]: { user: null, loading: false, error: "Search failed" },
      }))
    }
  }

  // Debounced search functions
  const debouncedSearchUser = debounce(searchUser, 500)

  const updateUser = async (data: UserUpdateRequest) => {
    setLoading(true)
    setError("")
    setSuccess("")

    try {
      const token = localStorage.getItem("adminToken")
      if (!token) {
        throw new Error("No authentication token found")
      }

      // const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/user/update`, {
      const response = await fetch('http://spotseeker-backend-env.eba-s3z34pvy.ap-south-1.elasticbeanstalk.com/api/user/update', {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      })

      const result = await response.json()

      if (response.ok) {
        setSuccess(`User updated successfully!`)
        // Reset forms and search results
        setStatusForm({ identifier: "", identifierType: "nic", status: "" })
        setActiveForm({ identifier: "", identifierType: "nic", isActive: "" })
        setRfidForm({ identifier: "", identifierType: "nic", newRfidTag: "" })
        setSearchResults({
          status: { user: null, loading: false, error: "" },
          active: { user: null, loading: false, error: "" },
          rfid: { user: null, loading: false, error: "" },
        })
      } else {
        setError(result.message || "Failed to update user")
      }
    } catch (error) {
      setError("Network error. Please check if the server is running.")
    } finally {
      setLoading(false)
    }
  }

  const handleStatusUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!statusForm.identifier || !statusForm.status) {
      setError("Please fill in all fields")
      return
    }

    const updateData: UserUpdateRequest = {
      status: statusForm.status,
    }

    if (statusForm.identifierType === "nic") {
      updateData.nic = statusForm.identifier
    } else {
      updateData.rfidTag = statusForm.identifier
    }

    await updateUser(updateData)
  }

  const handleActiveUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!activeForm.identifier || !activeForm.isActive) {
      setError("Please fill in all fields")
      return
    }

    const updateData: UserUpdateRequest = {
      isActive: activeForm.isActive === "true",
    }

    if (activeForm.identifierType === "nic") {
      updateData.nic = activeForm.identifier
    } else {
      updateData.rfidTag = activeForm.identifier
    }

    await updateUser(updateData)
  }

  const handleRfidUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!rfidForm.identifier || !rfidForm.newRfidTag) {
      setError("Please fill in all fields")
      return
    }

    const updateData: UserUpdateRequest = {
      rfidTag: rfidForm.newRfidTag,
    }

    if (rfidForm.identifierType === "nic") {
      updateData.nic = rfidForm.identifier
    } else {
      updateData.rfidTag = rfidForm.identifier
    }

    await updateUser(updateData)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "IN":
        return "bg-green-100 text-green-800 border-green-200"
      case "OUT":
        return "bg-red-100 text-red-800 border-red-200"
      case "IDLE":
        return "bg-yellow-100 text-yellow-800 border-yellow-200"
      default:
        return "bg-gray-100 text-gray-800 border-gray-200"
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="bg-white border-slate-300 text-gray-700 hover:bg-slate-50 transition-colors"
        >
          <Settings className="h-4 w-4 mr-2" />
          <span className="hidden sm:inline">User Management</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center text-xl font-bold text-gray-900">
            <UserCog className="h-6 w-6 mr-2 text-slate-600" />
            Manual User Override
          </DialogTitle>
          <DialogDescription className="text-gray-600">
            Manually update user status and active state for administrative purposes
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Alert Messages */}
          {error && (
            <Alert variant="destructive" className="bg-red-50 border-red-300 animate-in slide-in-from-top-2">
              <AlertCircle className="h-4 w-4 text-red-600" />
              <AlertDescription className="text-red-800">{error}</AlertDescription>
            </Alert>
          )}

          {success && (
            <Alert className="border-green-300 bg-green-50 animate-in slide-in-from-top-2">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800">{success}</AlertDescription>
            </Alert>
          )}

          {/* Status Reference Card */}
          {/* <Card className="bg-gradient-to-r from-slate-50 to-blue-50/50 border-0 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-700">Status Reference</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="flex flex-wrap gap-2">
                <Badge className={getStatusColor("IN")}>IN</Badge>
                <Badge className={getStatusColor("OUT")}>OUT</Badge>
                <Badge className={getStatusColor("IDLE")}>IDLE</Badge>
              </div>
            </CardContent>
          </Card> */}

          {/* Tabs for different update types */}
          <Tabs defaultValue="status" className="w-full">
            <TabsList className="grid w-full grid-cols-3 mb-6 bg-slate-100/80 p-1 rounded-lg">
              <TabsTrigger
                value="status"
                className="text-gray-700 data-[state=active]:bg-slate-800 data-[state=active]:text-white data-[state=active]:shadow-md transition-all duration-200"
              >
                <User className="h-4 w-4 mr-2" />
                Update Status
              </TabsTrigger>
              <TabsTrigger
                value="active"
                className="text-gray-700 data-[state=active]:bg-slate-800 data-[state=active]:text-white data-[state=active]:shadow-md transition-all duration-200"
              >
                <Power className="h-4 w-4 mr-2" />
                Update Active State
              </TabsTrigger>
              <TabsTrigger
                value="rfid"
                className="text-gray-700 data-[state=active]:bg-slate-800 data-[state=active]:text-white data-[state=active]:shadow-md transition-all duration-200"
              >
                <Settings className="h-4 w-4 mr-2" />
                Update RFID
              </TabsTrigger>
            </TabsList>

            {/* Status Update Tab */}
            <TabsContent value="status" className="space-y-4">
              <Card className="shadow-lg border-0 bg-white">
                <CardHeader className="bg-gradient-to-r from-slate-50 to-blue-50/50 rounded-t-lg">
                  <CardTitle className="text-gray-900 flex items-center">
                    <User className="h-5 w-5 mr-2 text-slate-600" />
                    Update User Status
                  </CardTitle>
                  <CardDescription className="text-gray-600">
                    Change user's current location status (IN, OUT, IDLE)
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-6 space-y-4">
                  <form onSubmit={handleStatusUpdate} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="status-type" className="text-gray-700 font-medium">
                        Identifier Type
                      </Label>
                      <Select
                        value={statusForm.identifierType}
                        onValueChange={(value: "rfidTag" | "nic") => {
                          setStatusForm({ ...statusForm, identifierType: value, identifier: "" })
                          setSearchResults((prev) => ({
                            ...prev,
                            status: { user: null, loading: false, error: "" },
                          }))
                        }}
                      >
                        <SelectTrigger className="bg-white border-slate-300 text-gray-900 focus:border-slate-600 focus:ring-slate-600/20">
                          <SelectValue placeholder="Select identifier type" />
                        </SelectTrigger>
                        <SelectContent>
                          {/* <SelectItem value="nic">NIC Number</SelectItem> */}
                          <SelectItem value="rfidTag">RFID Tag</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="status-identifier" className="text-gray-700 font-medium">
                        {statusForm.identifierType === "nic" ? "NIC Number" : "RFID Tag"}
                      </Label>
                      <Input
                        id="status-identifier"
                        type="text"
                        placeholder={statusForm.identifierType === "nic" ? "e.g., 991234567V" : "e.g., 1234567890"}
                        className="bg-white border-slate-300 text-gray-900 placeholder-gray-500 focus:border-slate-600 focus:ring-slate-600/20 transition-colors"
                        value={statusForm.identifier}
                        onChange={(e) => {
                          const value = e.target.value
                          setStatusForm({ ...statusForm, identifier: value })
                          debouncedSearchUser(value, "status")
                        }}
                        required
                      />
                    </div>
                    {/* User Display */}
                    {searchResults.status.loading && (
                      <div className="flex items-center text-sm text-gray-600">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
                        Searching...
                      </div>
                    )}
                    {searchResults.status.user && (
                    <div
                        className={`flex items-center p-3 border rounded-md ${
                          searchResults.status.user.isActive
                            ? "bg-green-50 border-green-200"
                            : "bg-red-50 border-red-200"
                        }`}
                      >
                        {searchResults.status.user.isActive ? (
                          <CheckCircle className="h-4 w-4 text-green-600 mr-2" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-600 mr-2" />
                        )}
                        <div>
                          {searchResults.status.user.isActive ? (
                            <p className="text-xs text-green-600">
                              Status: {searchResults.status.user.status} | Active: Yes
                            </p>
                          ) : (
                            <p className="text-xs text-red-600">
                              This RFID is not active. Please verify the tag or contact admin.
                            </p>
                          )}
                        </div>
                      </div>
                    )}
                    {searchResults.status.error && (
                      <div className="flex items-center p-3 bg-red-50 border border-red-200 rounded-md">
                        <AlertCircle className="h-4 w-4 text-red-600 mr-2" />
                        <p className="text-sm text-red-800">{searchResults.status.error}</p>
                      </div>
                    )}
                    <div className="space-y-2">
                      <Label htmlFor="status-select" className="text-gray-700 font-medium">
                        New Status
                      </Label>
                      <Select
                        value={statusForm.status}
                        onValueChange={(value: "IDLE" | "OUT" | "IN") =>
                          setStatusForm({ ...statusForm, status: value })
                        }
                      >
                        <SelectTrigger className="bg-white border-slate-300 text-gray-900 focus:border-slate-600 focus:ring-slate-600/20">
                          <SelectValue placeholder="Select new status" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="IN">
                            <div className="flex items-center">
                              <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                              IN - Inside Facility
                            </div>
                          </SelectItem>
                          <SelectItem value="OUT">
                            <div className="flex items-center">
                              <div className="w-2 h-2 bg-red-500 rounded-full mr-2"></div>
                              OUT - Outside Facility
                            </div>
                          </SelectItem>
                          <SelectItem value="IDLE">
                            <div className="flex items-center">
                              <div className="w-2 h-2 bg-yellow-500 rounded-full mr-2"></div>
                              IDLE - No Recent Activity
                            </div>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <Button
                      type="submit"
                      className="w-full bg-gradient-to-r from-slate-700 to-slate-800 hover:from-slate-800 hover:to-slate-900 text-white shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-[1.02]"
                      disabled={loading}
                    >
                      {loading ? (
                        <div className="flex items-center">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                          Updating Status...
                        </div>
                      ) : (
                        "Update User Status"
                      )}
                    </Button>
                  </form>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Active State Update Tab */}
            <TabsContent value="active" className="space-y-4">
              <Card className="shadow-lg border-0 bg-white">
                <CardHeader className="bg-gradient-to-r from-slate-50 to-blue-50/50 rounded-t-lg">
                  <CardTitle className="text-gray-900 flex items-center">
                    <Power className="h-5 w-5 mr-2 text-slate-600" />
                    Update Active State
                  </CardTitle>
                  <CardDescription className="text-gray-600">
                    Enable or disable user's access permissions
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-6 space-y-4">
                  <form onSubmit={handleActiveUpdate} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="active-type" className="text-gray-700 font-medium">
                        Identifier Type
                      </Label>
                      <Select
                        value={activeForm.identifierType}
                        onValueChange={(value: "nic" | "rfidTag") => {
                          setActiveForm({ ...activeForm, identifierType: value, identifier: "" })
                          setSearchResults((prev) => ({
                            ...prev,
                            active: { user: null, loading: false, error: "" },
                          }))
                        }}
                      >
                        <SelectTrigger className="bg-white border-slate-300 text-gray-900 focus:border-slate-600 focus:ring-slate-600/20">
                          <SelectValue placeholder="Select identifier type" />
                        </SelectTrigger>
                        <SelectContent>
                          {/* <SelectItem value="nic">NIC Number</SelectItem> */}
                          <SelectItem value="rfidTag">RFID Tag</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="active-identifier" className="text-gray-700 font-medium">
                        {activeForm.identifierType === "nic" ? "NIC Number" : "RFID Tag"}
                      </Label>
                      <Input
                        id="active-identifier"
                        type="text"
                        placeholder={activeForm.identifierType === "nic" ? "e.g., 991234567V" : "e.g., 1234567890"}
                        className="bg-white border-slate-300 text-gray-900 placeholder-gray-500 focus:border-slate-600 focus:ring-slate-600/20 transition-colors"
                        value={activeForm.identifier}
                        onChange={(e) => {
                          const value = e.target.value
                          setActiveForm({ ...activeForm, identifier: value })
                          debouncedSearchUser(value, "active")
                        }}
                        required
                      />
                    </div>
                    {/* User Display */}
                    {searchResults.active.loading && (
                      <div className="flex items-center text-sm text-gray-600">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
                        Searching...
                      </div>
                    )}
                    {searchResults.active.user && (
                    <div
                        className={`flex items-center p-3 border rounded-md ${
                          searchResults.active.user.isActive
                            ? "bg-green-50 border-green-200"
                            : "bg-red-50 border-red-200"
                        }`}
                      >
                        {searchResults.active.user.isActive ? (
                          <CheckCircle className="h-4 w-4 text-green-600 mr-2" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-600 mr-2" />
                        )}
                        <div>
                          {searchResults.active.user.isActive ? (
                            <p className="text-xs text-green-600">
                              Status: {searchResults.active.user.status} | Active: Yes
                            </p>
                          ) : (
                            <p className="text-xs text-red-600">
                              This RFID is not active. Please verify the tag or contact admin.
                            </p>
                          )}
                        </div>
                      </div>
                    )}
                    {searchResults.active.error && (
                      <div className="flex items-center p-3 bg-red-50 border border-red-200 rounded-md">
                        <AlertCircle className="h-4 w-4 text-red-600 mr-2" />
                        <p className="text-sm text-red-800">{searchResults.active.error}</p>
                      </div>
                    )}
                    <div className="space-y-2">
                      <Label htmlFor="active-select" className="text-gray-700 font-medium">
                        Active State
                      </Label>
                      <Select
                        value={activeForm.isActive}
                        onValueChange={(value: "true" | "false") => setActiveForm({ ...activeForm, isActive: value })}
                      >
                        <SelectTrigger className="bg-white border-slate-300 text-gray-900 focus:border-slate-600 focus:ring-slate-600/20">
                          <SelectValue placeholder="Select active state" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="true">
                            <div className="flex items-center">
                              <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                              Active
                            </div>
                          </SelectItem>
                          <SelectItem value="false">
                            <div className="flex items-center">
                              <div className="w-2 h-2 bg-red-500 rounded-full mr-2"></div>
                              Inactive
                            </div>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <Button
                      type="submit"
                      className="w-full bg-gradient-to-r from-slate-700 to-slate-800 hover:from-slate-800 hover:to-slate-900 text-white shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-[1.02]"
                      disabled={loading}
                    >
                      {loading ? (
                        <div className="flex items-center">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                          Updating Active State...
                        </div>
                      ) : (
                        "Update Active State"
                      )}
                    </Button>
                  </form>
                </CardContent>
              </Card>
            </TabsContent>

            {/* RFID Update Tab */}
            <TabsContent value="rfid" className="space-y-4">
              <Card className="shadow-lg border-0 bg-white">
                <CardHeader className="bg-gradient-to-r from-slate-50 to-blue-50/50 rounded-t-lg">
                  <CardTitle className="text-gray-900 flex items-center">
                    <Settings className="h-5 w-5 mr-2 text-slate-600" />
                    Update RFID Tag
                  </CardTitle>
                  <CardDescription className="text-gray-600">Assign or update user's RFID tag</CardDescription>
                </CardHeader>
                <CardContent className="p-6 space-y-4">
                  <form onSubmit={handleRfidUpdate} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="rfid-type" className="text-gray-700 font-medium">
                        Identifier Type
                      </Label>
                      <Select
                        value={rfidForm.identifierType}
                        onValueChange={(value: "nic" | "rfidTag") => {
                          setRfidForm({ ...rfidForm, identifierType: value, identifier: "" })
                          setSearchResults((prev) => ({
                            ...prev,
                            rfid: { user: null, loading: false, error: "" },
                          }))
                        }}
                      >
                        <SelectTrigger className="bg-white border-slate-300 text-gray-900 focus:border-slate-600 focus:ring-slate-600/20">
                          <SelectValue placeholder="Select identifier type" />
                        </SelectTrigger>
                        <SelectContent>
                          {/* <SelectItem value="nic">NIC Number</SelectItem> */}
                          <SelectItem value="rfidTag">Current RFID Tag</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="rfid-identifier" className="text-gray-700 font-medium">
                        {rfidForm.identifierType === "nic" ? "NIC Number" : "Current RFID Tag"}
                      </Label>
                      <Input
                        id="rfid-identifier"
                        type="text"
                        placeholder={rfidForm.identifierType === "nic" ? "e.g., 991234567V" : "e.g., 1234567890"}
                        className="bg-white border-slate-300 text-gray-900 placeholder-gray-500 focus:border-slate-600 focus:ring-slate-600/20 transition-colors"
                        value={rfidForm.identifier}
                        onChange={(e) => {
                          const value = e.target.value
                          setRfidForm({ ...rfidForm, identifier: value })
                          debouncedSearchUser(value, "rfid")
                        }}
                        required
                      />
                    </div>
                    {/* User Display */}
                    {searchResults.rfid.loading && (
                      <div className="flex items-center text-sm text-gray-600">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
                        Searching...
                      </div>
                    )}
                    {searchResults.rfid.user && (
                      <div
                        className={`flex items-center p-3 border rounded-md ${
                          searchResults.rfid.user.isActive
                            ? "bg-green-50 border-green-200"
                            : "bg-red-50 border-red-200"
                        }`}
                      >
                        {searchResults.rfid.user.isActive ? (
                          <CheckCircle className="h-4 w-4 text-green-600 mr-2" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-600 mr-2" />
                        )}
                        <div>
                          {searchResults.rfid.user.isActive ? (
                            <p className="text-xs text-green-600">
                              Current RFID: {searchResults.rfid.user.rfidTag || "None"} | Active: Yes
                            </p>
                          ) : (
                            <p className="text-xs text-red-600">
                              This RFID is not active. Please verify the tag or contact admin.
                            </p>
                          )}
                        </div>
                      </div>
                    )}
                    {searchResults.rfid.error && (
                      <div className="flex items-center p-3 bg-red-50 border border-red-200 rounded-md">
                        <AlertCircle className="h-4 w-4 text-red-600 mr-2" />
                        <p className="text-sm text-red-800">{searchResults.rfid.error}</p>
                      </div>
                    )}
                    <div className="space-y-2">
                      <Label htmlFor="new-rfid" className="text-gray-700 font-medium">
                        New RFID Tag
                      </Label>
                      <Input
                        id="new-rfid"
                        type="text"
                        placeholder="e.g., 9876543210"
                        className="bg-white border-slate-300 text-gray-900 placeholder-gray-500 focus:border-slate-600 focus:ring-slate-600/20 transition-colors"
                        value={rfidForm.newRfidTag}
                        onChange={(e) => setRfidForm({ ...rfidForm, newRfidTag: e.target.value })}
                        required
                      />
                    </div>
                    <Button
                      type="submit"
                      className="w-full bg-gradient-to-r from-slate-700 to-slate-800 hover:from-slate-800 hover:to-slate-900 text-white shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-[1.02]"
                      disabled={loading}
                    >
                      {loading ? (
                        <div className="flex items-center">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                          Updating RFID Tag...
                        </div>
                      ) : (
                        "Update RFID Tag"
                      )}
                    </Button>
                  </form>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </DialogContent>
    </Dialog>
  )
}
