"use client"

import { useState, useEffect } from "react"
import useSWR, { SWRConfig } from "swr"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Users,
  UserCheck,
  UserX,
  Clock,
  LogOut,
  Activity,
  RefreshCw,
  TrendingUp,
  Database,
  Search,
  Filter,
  Download,
  Calendar,
  MapPin,
  WifiOff,
  AlertTriangle,
  CheckCircle,
} from "lucide-react"
import { apiUrls } from "@/lib/api"
import UserManagementModal from "@/components/user-management-modal"
import * as XLSX from "xlsx"

interface Summary {
  total_users: number
  in_users: number
  out_users: number
  idle_users: number
}

interface User {
  id: number
  name: string
  nic: string
  rfidTag: string
  status: string
  isActive: boolean
}

interface Log {
  id: number
  userId: number
  eventType: string
  gateLocation: string
  deviceId: string
  timestamp: string
  result: string
  message: string
  user: User
}

interface AnalyticsResponse {
  summary: Summary
}

interface LogsResponse {
  logs: Log[]
}

interface HealthResponse {
  status: string
  dataAvailable: boolean
  message?: string
}

// Custom fetcher with authorization
const fetcher = async (url: string) => {
  const token = localStorage.getItem("adminToken")
  if (!token) {
    throw new Error("No authentication token found")
  }

  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  })

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem("adminToken")
      window.location.href = "/"
      throw new Error("Authentication failed")
    }
    throw new Error("Failed to fetch data")
  }

  return response.json()
}

// Health fetcher without auth
const healthFetcher = async (url: string) => {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
    },
  })

  if (!response.ok) {
    throw new Error("Backend offline")
  }

  return response.json()
}

// System Health Component
function SystemHealth() {
  const { data: healthData, error: healthError } = useSWR<HealthResponse>(apiUrls.health(), healthFetcher, {
    refreshInterval: 2000,
    revalidateOnFocus: true,
    shouldRetryOnError: false,
  })

  const getSystemStatus = () => {
    if (healthError) {
      return {
        status: "offline",
        label: "OFFLINE",
        color: "bg-red-500",
        textColor: "text-red-600",
        bgColor: "bg-red-50",
        borderColor: "border-red-200",
        icon: WifiOff,
        description: "Backend server is not responding",
      }
    }

    if (healthData) {
      if (healthData.status === "ok" && healthData.dataAvailable && !healthData.message) {
        return {
          status: "online",
          label: "ONLINE",
          color: "bg-green-500",
          textColor: "text-green-600",
          bgColor: "bg-green-50",
          borderColor: "border-green-200",
          icon: CheckCircle,
          description: "All systems operational",
        }
      } else {
        return {
          status: "error",
          label: "ERROR",
          color: "bg-yellow-500",
          textColor: "text-yellow-600",
          bgColor: "bg-yellow-50",
          borderColor: "border-yellow-200",
          icon: AlertTriangle,
          description: healthData.message || "Backend online but data unavailable",
        }
      }
    }

    return {
      status: "checking",
      label: "CHECKING",
      color: "bg-gray-500",
      textColor: "text-gray-600",
      bgColor: "bg-gray-50",
      borderColor: "border-gray-200",
      icon: Activity,
      description: "Checking system status...",
    }
  }

  const systemStatus = getSystemStatus()
  const StatusIcon = systemStatus.icon

  return (
    <Card
      className={`shadow-md transition-all duration-300 hover:shadow-lg border-0 ${systemStatus.bgColor} ${systemStatus.borderColor} border-l-4 rounded-lg`}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="text-sm font-medium text-gray-600">SYSTEM STATUS</CardTitle>
        <div className="flex items-center space-x-1.5">
          <div className={`w-2 h-2 rounded-full ${systemStatus.color} animate-pulse`}></div>
          <StatusIcon className={`h-4 w-4 ${systemStatus.textColor} opacity-80`} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-end justify-between">
          <div>
            <p className={`text-xs ${systemStatus.textColor} opacity-90 font-normal mb-1`}>Current system status</p>
            <div className={`text-3xl font-bold ${systemStatus.textColor}`}>{systemStatus.label}</div>
          </div>
        </div>
        <div className="mt-4 pt-3 border-t border-opacity-20 border-gray-400">
          <p className={`text-sm ${systemStatus.textColor} font-medium`}>{systemStatus.description}</p>
          <div className="text-xs text-gray-500 mt-2">Last updated: {new Date().toLocaleTimeString()}</div>
        </div>
      </CardContent>
    </Card>
  )
}

function DashboardContent() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [searchTerm, setSearchTerm] = useState("")
  const [eventFilter, setEventFilter] = useState("")
  const [resultFilter, setResultFilter] = useState("")
  const [isExporting, setIsExporting] = useState(false)
  const [itemsPerPage, setItemsPerPage] = useState(10)
  const [currentPage, setCurrentPage] = useState(1)

  // Check authentication on mount
  useEffect(() => {
    const token = localStorage.getItem("adminToken")
    if (!token) {
      window.location.href = "/"
      return
    }
    setIsAuthenticated(true)
  }, [])

  // SWR hooks for real-time data
  const {
    data: analyticsData,
    error: analyticsError,
    mutate: mutateAnalytics,
  } = useSWR<AnalyticsResponse>(isAuthenticated ? apiUrls.analytics() : null, fetcher, {
    refreshInterval: 5000,
    revalidateOnFocus: true,
  })

  const {
    data: logsData,
    error: logsError,
    mutate: mutateLogs,
  } = useSWR<LogsResponse>(isAuthenticated ? apiUrls.logs() : null, fetcher, {
    refreshInterval: 3000,
    revalidateOnFocus: true,
  })

  const handleLogout = () => {
    localStorage.removeItem("adminToken")
    window.location.href = "/"
  }

  const handleRefresh = () => {
    mutateAnalytics()
    mutateLogs()
  }

  const filteredLogs =
    logsData?.logs.filter((log) => {
      const matchesSearch =
        searchTerm === "" ||
        log.user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.user.nic.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.user.rfidTag.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.gateLocation.toLowerCase().includes(searchTerm.toLowerCase())

      const matchesEvent = eventFilter === "" || log.eventType === eventFilter
      const matchesResult = resultFilter === "" || log.result === resultFilter

      return matchesSearch && matchesEvent && matchesResult
    }) || []

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
  }

  // Excel Export Function
  const handleExportToExcel = () => {
    if (!logsData?.logs || logsData.logs.length === 0) {
      alert("No data available to export")
      return
    }

    setIsExporting(true)

    try {
      // Determine which data to export
      const hasFilters = searchTerm !== "" || eventFilter !== "" || resultFilter !== ""
      const dataToExport = hasFilters ? filteredLogs : logsData.logs

      if (dataToExport.length === 0) {
        alert("No data matches the current filters")
        setIsExporting(false)
        return
      }

      // Prepare data for Excel export
      const excelData = dataToExport.map((log, index) => ({
        "S.No": index + 1,
        "RFID Tag": log.user?.rfidTag ?? "N/A",
        "User Status": log.user?.status ?? "N/A",
        "Event Type": log.eventType === "IN" ? "ENTRY" : log.eventType === "OUT" ? "EXIT" : "OTHER",
        "Gate Location": log.gateLocation,
        "Device ID": log.deviceId,
        "Access Result": log.result,
        Message: log.message || "",
        Date: new Date(log.timestamp).toLocaleDateString(),
        Time: new Date(log.timestamp).toLocaleTimeString(),
        "Full Timestamp": formatTimestamp(log.timestamp),
        "User Active": log.user?.isActive ? "Yes" : "No",
      }))

      // Create workbook and worksheet
      const workbook = XLSX.utils.book_new()
      const worksheet = XLSX.utils.json_to_sheet(excelData)

      // Set column widths for better readability
      const columnWidths = [
        { wch: 8 }, // S.No
        { wch: 15 }, // RFID Tag
        { wch: 12 }, // User Status
        { wch: 12 }, // Event Type
        { wch: 20 }, // Gate Location
        { wch: 15 }, // Device ID
        { wch: 12 }, // Access Result
        { wch: 30 }, // Message
        { wch: 12 }, // Date
        { wch: 12 }, // Time
        { wch: 20 }, // Full Timestamp
        { wch: 12 }, // User Active
      ]
      worksheet["!cols"] = columnWidths

      // Add worksheet to workbook
      XLSX.utils.book_append_sheet(workbook, worksheet, "Access Control Logs")

      // Generate filename with current date and filter status
      const currentDate = new Date().toISOString().split("T")[0]
      const filterStatus = hasFilters ? "_Filtered" : "_Complete"
      const filename = `Access_Control_Logs_${currentDate}${filterStatus}.xlsx`

      // Export the file
      XLSX.writeFile(workbook, filename)

      // Show success message
      const exportMessage = hasFilters
        ? `Successfully exported ${dataToExport.length} filtered records to Excel`
        : `Successfully exported all ${dataToExport.length} records to Excel`

      alert(exportMessage)
    } catch (error) {
      console.error("Export failed:", error)
      alert("Failed to export data. Please try again.")
    } finally {
      setIsExporting(false)
    }
  }

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [searchTerm, eventFilter, resultFilter])

  // Pagination calculations
  const totalItems = filteredLogs.length
  const totalPages = Math.ceil(totalItems / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage
  const currentPageData = filteredLogs.slice(startIndex, endIndex)

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  const handlePreviousPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1)
    }
  }

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1)
    }
  }

  // Generate page numbers for pagination
  const getPageNumbers = () => {
    const pages = []
    const maxVisiblePages = 5

    if (totalPages <= maxVisiblePages) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i)
      }
    } else {
      if (currentPage <= 3) {
        for (let i = 1; i <= 4; i++) {
          pages.push(i)
        }
        pages.push("...")
        pages.push(totalPages)
      } else if (currentPage >= totalPages - 2) {
        pages.push(1)
        pages.push("...")
        for (let i = totalPages - 3; i <= totalPages; i++) {
          pages.push(i)
        }
      } else {
        pages.push(1)
        pages.push("...")
        for (let i = currentPage - 1; i <= currentPage + 1; i++) {
          pages.push(i)
        }
        pages.push("...")
        pages.push(totalPages)
      }
    }

    return pages
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-slate-200 border-t-slate-800 mx-auto mb-4"></div>
          <p className="text-slate-700 font-medium text-lg">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header matching auth-page style */}
      <header className="fixed top-0 left-0 right-0 bg-white border-b border-slate-200 shadow-sm z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-20">
            <div className="flex items-center">
              <div className="relative">
                <img src="/images/logo.webp" alt="SPOTSEEKER.LK Logo" className="h-10 w-auto mr-4" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">ACCESS PRO</h1>
                <p className="text-red-600 text-sm font-medium">Security Dashboard</p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <UserManagementModal />
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                className="bg-white border-slate-300 text-gray-700 hover:bg-slate-50 transition-colors"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                <span className="hidden sm:inline">Refresh</span>
              </Button>
              <Button
                onClick={handleLogout}
                className="bg-gradient-to-r from-slate-700 to-slate-800 hover:from-slate-800 hover:to-slate-900 text-white shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-[1.02]"
              >
                <LogOut className="h-4 w-4 mr-2" />
                <span className="hidden sm:inline">Logout</span>
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pt-28">
        {/* Analytics Cards */}
        <div className="mb-8">
          <div className="flex items-center mb-6">
            <TrendingUp className="h-6 w-6 text-slate-600 mr-3" />
            <h2 className="text-2xl font-bold text-gray-900">Access Analytics</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
            {/* System Health Card - First Position */}
            <SystemHealth />

            <Card className="shadow-md border-0 bg-white">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 bg-gradient-to-r from-slate-50 to-blue-50/50 rounded-t-lg">
                <CardTitle className="text-sm font-medium text-gray-700">Total Users</CardTitle>
                <div className="p-2 bg-slate-100 rounded-full">
                  <Users className="h-5 w-5 text-slate-600" />
                </div>
              </CardHeader>
              <CardContent className="bg-white">
                <div className="flex items-center justify-center h-[80px] pt-14">
                  <div className="text-4xl font-medium text-gray-900 tracking-tight bg-clip-text bg-gradient-to-br from-blue-600 to-blue-400">
                    {analyticsData?.summary.total_users ?? "—"}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-md border-0 bg-white">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 bg-gradient-to-r from-slate-50 to-green-50/50 rounded-t-lg">
                <CardTitle className="text-sm font-medium text-gray-700">Users Inside</CardTitle>
                <div className="p-2 bg-green-100 rounded-full">
                  <UserCheck className="h-5 w-5 text-green-600" />
                </div>
              </CardHeader>
              <CardContent className="bg-white">
                <div className="flex items-center justify-center h-[80px] pt-14">
                  <div className="text-4xl font-medium text-green-600 tracking-tight bg-clip-text bg-gradient-to-br from-green-600 to-green-400">
                    {analyticsData?.summary.in_users ?? "—"}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-md border-0 bg-white">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 bg-gradient-to-r from-slate-50 to-red-50/50 rounded-t-lg">
                <CardTitle className="text-sm font-medium text-gray-700">Users Outside</CardTitle>
                <div className="p-2 bg-red-100 rounded-full">
                  <UserX className="h-5 w-5 text-red-600" />
                </div>
              </CardHeader>
              <CardContent className="bg-white">
                <div className="flex items-center justify-center h-[80px] pt-14">
                  <div className="text-4xl font-medium text-red-600 tracking-tight bg-clip-text bg-gradient-to-br from-red-600 to-red-400">
                    {analyticsData?.summary.out_users ?? "—"}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-md border-0 bg-white">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 bg-gradient-to-r from-slate-50 to-yellow-50/50 rounded-t-lg">
                <CardTitle className="text-sm font-medium text-gray-700">Idle Users</CardTitle>
                <div className="p-2 bg-yellow-100 rounded-full">
                  <Clock className="h-5 w-5 text-yellow-600" />
                </div>
              </CardHeader>
              <CardContent className="bg-white">
                <div className="flex items-center justify-center h-[80px] pt-14">
                  <div className="text-4xl font-medium text-yellow-600 tracking-tight bg-clip-text bg-gradient-to-br from-yellow-600 to-yellow-400">
                    {analyticsData?.summary.idle_users ?? "—"}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Activity Logs */}
        <div>
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center">
              <Database className="h-6 w-6 text-slate-600 mr-3" />
              <h2 className="text-2xl font-bold text-gray-900">Access Control Logs</h2>
              <Badge variant="outline" className="ml-3 bg-blue-50 text-blue-700 border-blue-200">
                {filteredLogs.length.toLocaleString()} entries
              </Badge>
            </div>
            <div className="flex items-center space-x-3">
              <div className="flex items-center text-sm text-slate-600 bg-slate-100/80 px-3 py-1 rounded-lg">
                <Activity className="h-4 w-4 mr-2 animate-pulse text-green-500" />
                Live updates
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleExportToExcel}
                disabled={isExporting || !logsData?.logs || logsData.logs.length === 0}
                className="bg-white border-slate-300 text-gray-700 hover:bg-slate-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Download className="h-4 w-4 mr-2" />
                {isExporting ? "Exporting..." : "Export"}
              </Button>
            </div>
          </div>

          <Card className="shadow-lg border-0 bg-white overflow-hidden">
            {/* Enhanced Header with Search and Filters */}
            <CardHeader className="bg-gradient-to-r from-slate-50 to-blue-50/50 border-b border-slate-200">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Activity className="h-5 w-5 mr-2 text-slate-600" />
                    <CardTitle className="text-gray-900">Real-time Access Monitoring</CardTitle>
                  </div>
                  <div className="flex items-center space-x-2">
                    <select
                      value={itemsPerPage}
                      onChange={(e) => {
                        setItemsPerPage(Number(e.target.value))
                        setCurrentPage(1) // Reset to first page when changing items per page
                      }}
                      className="text-sm border border-slate-300 rounded-md px-3 py-1.5 bg-white text-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="10">Show 10</option>
                      <option value="25">Show 25</option>
                      <option value="50">Show 50</option>
                      <option value="100">Show 100</option>
                    </select>
                  </div>
                </div>

                {/* Search and Filter Bar */}
                <div className="flex flex-col sm:flex-row gap-3">
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <input
                      type="text"
                      placeholder="Search by name, NIC, RFID, or location..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full pl-10 pr-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white text-sm"
                    />
                  </div>
                  <div className="flex gap-2">
                    <select
                      value={eventFilter}
                      onChange={(e) => setEventFilter(e.target.value)}
                      className="text-sm border border-slate-300 rounded-lg px-3 py-2.5 bg-white text-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="">All Events</option>
                      <option value="IN">Entry Only</option>
                      <option value="OUT">Exit Only</option>
                    </select>
                    <select
                      value={resultFilter}
                      onChange={(e) => setResultFilter(e.target.value)}
                      className="text-sm border border-slate-300 rounded-lg px-3 py-2.5 bg-white text-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="">All Results</option>
                      <option value="GRANTED">Granted</option>
                      <option value="DENIED">Denied</option>
                    </select>
                  </div>
                </div>

                {/* Export Status Indicator */}
                {(searchTerm !== "" || eventFilter !== "" || resultFilter !== "") && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <div className="flex items-center text-sm text-blue-800">
                      <Filter className="h-4 w-4 mr-2" />
                      <span className="font-medium">Filters Active:</span>
                      <span className="ml-2">
                        Export will include only filtered data ({filteredLogs.length} records)
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </CardHeader>

            <CardContent className="p-0 bg-white">
              {!logsData ? (
                <div className="flex items-center justify-center py-20">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-4 border-slate-200 border-t-slate-800 mx-auto mb-4"></div>
                    <span className="text-gray-700 font-medium text-lg">Loading access logs...</span>
                    <p className="text-sm text-gray-500 mt-2">Fetching real-time data</p>
                  </div>
                </div>
              ) : logsData.logs.length === 0 ? (
                <div className="text-center py-20 text-gray-500">
                  <Database className="h-20 w-20 mx-auto mb-6 text-gray-300" />
                  <p className="text-xl font-medium mb-2">No access logs found</p>
                  <p className="text-sm text-gray-400">Access events will appear here in real-time</p>
                </div>
              ) : (
                <div className="relative">
                  {/* Compact Table Header */}
                  <div className="sticky top-0 bg-white border-b-2 border-slate-200 z-10">
                    <div className={`grid grid-cols-6 gap-4 py-4 px-6 text-sm font-semibold text-gray-900 bg-slate-50`}>
                      <div className="col-span-1 flex items-center h-12">User Information</div>
                      <div className="col-span-1 flex items-center justify-center h-12">Request</div>
                      <div className="col-span-1 flex items-center h-12">Gate</div>
                      <div className="col-span-1 flex items-center h-12">Device</div>
                      <div className="col-span-1 flex items-center justify-center h-12">Status</div>
                      <div className="col-span-1 flex items-center h-12">Message</div>
                    </div>
                  </div>

                  {/* Scrollable Log Entries */}
                  <div className="max-h-[600px] overflow-y-scroll">
                    {currentPageData.map((log, index) => (
                      <div
                        key={log.id}
                        className={`grid grid-cols-6 gap-4 py-4 px-6 border-b border-gray-100 hover:bg-blue-50/30 transition-all duration-150 items-center min-h-[80px] ${
                          index % 2 === 0 ? "bg-white" : "bg-gray-50/40"
                        } ${log.result === "DENIED" ? "border-l-4 border-l-red-400 bg-red-50/20" : ""}`}
                      >
                        {/* User Information */}
                        <div className="col-span-1 flex items-center h-full">
                          <div className="flex items-center space-x-3 w-full">
                            <div className="min-w-0 flex-1">
                              <div className="text-sm font-bold font-mono mb-1">RFID: {log.user?.rfidTag || "N/A"}</div>
                              <div className="text-xs text-gray-500 flex items-center">
                                <Calendar className="h-3 w-3 mr-1 text-slate-400" />
                                <div>
                                  <span className="font-medium">{new Date(log.timestamp).toLocaleDateString()}</span>
                                  <span className="ml-2 text-gray-400">
                                    {new Date(log.timestamp).toLocaleTimeString()}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Event Type */}
                        <div className="col-span-1 flex justify-center items-center h-full">
                          <p>{log.eventType === "IN" ? "ENTRY" : log.eventType === "OUT" ? "EXIT" : "OTHER"}</p>
                        </div>

                        {/* Location */}
                        <div className="col-span-1 flex items-center h-full">
                          <div className="flex items-center text-gray-900 font-medium text-sm w-full">
                            <MapPin className="h-4 w-4 mr-2 text-slate-600 flex-shrink-0" />
                            <span className="truncate">{log.gateLocation}</span>
                          </div>
                        </div>

                        {/* Device */}
                        <div className="col-span-1 flex items-center h-full">
                          <div className="text-gray-700 text-xs font-mono bg-gray-100 rounded-md px-2 py-1 inline-block border border-gray-200 truncate max-w-full">
                            {log.deviceId}
                          </div>
                        </div>

                        {/* Status */}
                        <div className="col-span-1 flex justify-center items-center pl-6 h-full">
                          <p
                            className={`text-xs font-bold ${
                              log.result === "GRANTED"
                                ? "text-green-800 border-green-300"
                                : "text-red-800 border-red-300"
                            }`}
                          >
                            {log.result}
                          </p>
                        </div>

                        {/* Message */}
                        <div className="col-span-1 pl-4 flex items-center h-full">
                          <div
                            className="text-gray-700 text-xs truncate max-w-full"
                            title={log.message || "No message"}
                          >
                            {log.message || "—"}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="border-t border-slate-200 bg-slate-50 px-6 py-4">
                      <div className="flex items-center justify-between">
                        <div className="text-sm text-gray-600">
                          Showing {startIndex + 1} to {Math.min(endIndex, totalItems)} of {totalItems.toLocaleString()}{" "}
                          entries
                        </div>
                        <div className="flex items-center space-x-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handlePreviousPage}
                            disabled={currentPage === 1}
                            className="bg-white border-slate-300 text-gray-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            Previous
                          </Button>
                          <div className="flex items-center space-x-1">
                            {getPageNumbers().map((page, index) => (
                              <div key={index}>
                                {page === "..." ? (
                                  <span className="text-gray-500 px-2">...</span>
                                ) : (
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => handlePageChange(page as number)}
                                    className={`${
                                      currentPage === page
                                        ? "bg-blue-600 text-white border-blue-600"
                                        : "bg-white border-slate-300 text-gray-700 hover:bg-slate-50"
                                    }`}
                                  >
                                    {page}
                                  </Button>
                                )}
                              </div>
                            ))}
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handleNextPage}
                            disabled={currentPage === totalPages}
                            className="bg-white border-slate-300 text-gray-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            Next
                          </Button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}

export default function Dashboard() {
  return (
    <SWRConfig
      value={{
        errorRetryCount: 3,
        errorRetryInterval: 5000,
      }}
    >
      <DashboardContent />
    </SWRConfig>
  )
}
