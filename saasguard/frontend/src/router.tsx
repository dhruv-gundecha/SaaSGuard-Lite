import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { AuditPage } from "./pages/AuditPage";
import { ExportsPage } from "./pages/ExportsPage";
import { HomePage } from "./pages/HomePage";
import { JobDetailPage } from "./pages/JobDetailPage";
import { JobsPage } from "./pages/JobsPage";
import { LoginPage } from "./pages/LoginPage";
import { OperationsPage } from "./pages/OperationsPage";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/",
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: "exports",
        element: <ExportsPage />,
      },
      {
        path: "jobs",
        element: <JobsPage />,
      },
      {
        path: "jobs/:jobId",
        element: <JobDetailPage />,
      },
      {
        path: "audit",
        element: <AuditPage />,
      },
      {
        path: "operations",
        element: <OperationsPage />,
      },
    ],
  },
]);
