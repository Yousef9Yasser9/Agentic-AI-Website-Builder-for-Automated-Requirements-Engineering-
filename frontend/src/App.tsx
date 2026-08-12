import { AppRoutes } from "./routes/AppRoutes";
import { ThemeController } from "./components/theme/ThemeController";
import { ToastContainer } from "./components/ui/Toast";

export default function App() {
  return (
    <>
      <ThemeController />
      <AppRoutes />
      <ToastContainer />
    </>
  );
}
