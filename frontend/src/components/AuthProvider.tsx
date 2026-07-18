"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  ApiUser,
  getCurrentUser,
  loginUser,
  LoginPayload,
  registerUser,
  RegisterPayload,
} from "@/lib/api";
import {
  clearAccessToken,
  getAccessToken,
  saveAccessToken,
} from "@/lib/auth-storage";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

type AuthContextValue = {
  user: ApiUser | null;
  token: string | null;
  status: AuthStatus;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

type AuthProviderProps = {
  children: ReactNode;
};

export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter();

  const [user, setUser] = useState<ApiUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  useEffect(() => {
    const storedToken = getAccessToken();

    if (!storedToken) {
      setStatus("unauthenticated");
      return;
    }

    setToken(storedToken);

    getCurrentUser(storedToken)
      .then((currentUser) => {
        setUser(currentUser);
        setStatus("authenticated");
      })
      .catch(() => {
        clearAccessToken();
        setToken(null);
        setUser(null);
        setStatus("unauthenticated");
      });
  }, []);

  async function login(payload: LoginPayload): Promise<void> {
    const loginResponse = await loginUser(payload);

    saveAccessToken(loginResponse.access_token);
    setToken(loginResponse.access_token);

    const currentUser = await getCurrentUser(loginResponse.access_token);

    setUser(currentUser);
    setStatus("authenticated");
    router.push("/dashboard");
  }

  async function register(payload: RegisterPayload): Promise<void> {
    await registerUser(payload);

    await login({
      email: payload.email,
      password: payload.password,
    });
  }

  function logout(): void {
    clearAccessToken();
    setToken(null);
    setUser(null);
    setStatus("unauthenticated");
    router.push("/login");
  }

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      status,
      login,
      register,
      logout,
    }),
    [user, token, status],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }

  return context;
}
