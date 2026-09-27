"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";
import {
  Activity,
  AirVent,
  ArrowUpRight,
  Bot,
  Check,
  ChevronDown,
  ChevronRight,
  ChevronsDown,
  ChevronsUp,
  CircleGauge,
  Clock3,
  CloudSun,
  Cpu,
  Droplets,
  Fish,
  GitBranch,
  Grid2X2,
  Grip,
  Home,
  Lightbulb,
  LayoutDashboard,
  ListTodo,
  LoaderCircle,
  Map,
  Mic,
  Minus,
  Network,
  PanelTop,
  PanelLeftClose,
  Pause,
  Play,
  Plus,
  Refrigerator,
  Router,
  RotateCw,
  Server,
  Settings2,
  ShieldCheck,
  Smartphone,
  Speaker,
  Sun,
  Thermometer,
  Trash2,
  Tv,
  Wifi,
  Workflow,
  Wrench,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Progress } from "@/components/ui/progress";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Toaster } from "@/components/ui/sonner";

type DeviceStatus = "online" | "busy" | "idle" | "offline" | "warning";
type WidgetSize = "compact" | "standard" | "wide" | "large";
type DeviceControl = "power" | "router" | "robot" | "aquarium" | "split-curtain" | "roller-curtain" | "climate" | "dimmable-light" | "energy" | "voice" | "presence" | "hub-usage" | "server-health" | "status";
type TaskQueue = "normal" | "priority";
type TaskStatus = "running" | "queued" | "done" | "failed" | "cancelled";
type TaskTerminalStatus = Extract<TaskStatus, "done" | "failed" | "cancelled">;
type CapabilityRisk = "normal" | "high";
type CapabilityParameters = Record<string, string | number | boolean>;
type DeviceCapability = { capabilityId: string; write: boolean; risk: CapabilityRisk };
type CapabilityCommand = DeviceCapability & {
  label: string;
  parameters: CapabilityParameters;
  queue?: TaskQueue;
  realtime?: boolean;
  duration?: number;
  outcome?: "done" | "failed";
};
type CapabilityCommandInput = Omit<CapabilityCommand, "write" | "risk" | "parameters"> & {
  write?: boolean;
  risk?: CapabilityRisk;
  parameters?: CapabilityParameters;
};
type DispatchDeviceAction = (device: Device, command: CapabilityCommand) => Promise<TaskTerminalStatus>;

type Device = {
  id: string;
  name: string;
  model: string;
  brand: string;
  room: string;
  status: DeviceStatus;
  icon: string;
  control: DeviceControl;
  metrics: string[];
  actions: string[];
  ip?: string;
  risk?: CapabilityRisk;
  capabilities?: Record<string, DeviceCapability>;
};

type Task = {
  id: string;
  title: string;
  device: string;
  status: TaskStatus;
  queue: TaskQueue;
  transport: "async";
  realtime: boolean;
  progress: number;
  time: string;
  capabilityId?: string;
  parameters?: CapabilityParameters;
  risk?: CapabilityRisk;
};

type TaskRuntime = {
  startTimer: number;
  ticker?: number;
  settled: boolean;
  resolve: (status: TaskTerminalStatus) => void;
};

type ConfirmationRequest = {
  id: string;
  device: Device;
  command: CapabilityCommand;
  resolve: (confirmed: boolean) => void;
};

type DeviceProfile = {
  id: string;
  name: string;
  description: string;
  icon: string;
  control: DeviceControl;
  defaultMetrics: string[];
};

type StepBinding = { id: string; deviceId: string; deviceName: string; action: string };
type PlanStepStatus = "draft" | "queued" | "running" | "success" | "failed" | "cancelled" | "skipped";
type PlanStep = { id: string; title: string; bindings: StepBinding[]; status: PlanStepStatus; result?: string };
type AutomationItem = { title: string; icon: LucideIcon; state: string; meta: string; steps: string[] };

// Public demo fixture only. Names, models, addresses, rooms, states and positions are fictional.
const initialDevices: Device[] = [
  { id: "hub-demo", name: "示例智能中枢", model: "Demo Hub H1", brand: "示例品牌", room: "书房", status: "online", icon: "hub", control: "hub-usage", ip: "hub.demo.local", metrics: ["5 小时剩余 72%", "每周剩余 84%", "预充值 ¥128"], actions: ["运行状态", "服务管理", "规则执行", "设备发现"] },
  { id: "data-demo", name: "示例数据中心", model: "Demo Vault D4", brand: "示例品牌", room: "书房", status: "busy", icon: "nas", control: "server-health", ip: "vault.demo.local", metrics: ["服务 18/18", "CPU 21% · 内存 48%", "存储 61%"], actions: ["浏览文件", "执行备份", "查看用电", "安全关机"] },
  { id: "router-core-demo", name: "示例主路由", model: "Demo Router R1", brand: "示例品牌", room: "客厅", status: "online", icon: "router", control: "router", ip: "router.demo.local", metrics: ["下载 128 Mbps", "上传 36 Mbps", "设备 20"], actions: ["网络状态", "访客网络", "设备隔离", "优先级设置"] },
  { id: "router-mesh-demo", name: "示例 Mesh 节点", model: "Demo Mesh M1", brand: "示例品牌", room: "主卧", status: "online", icon: "router", control: "router", ip: "mesh.demo.local", metrics: ["延迟 8 ms", "客户端 6", "信号 -41 dBm"], actions: ["网络状态", "Mesh 管理", "重新启动"] },
  { id: "display-demo", name: "客厅显示屏", model: "Demo Display 75", brand: "示例品牌", room: "客厅", status: "idle", icon: "tv", control: "power", metrics: ["待机", "HDMI 1", "局域网投屏"], actions: ["开关", "选择信号源", "播放", "音量"] },
  { id: "media-demo", name: "流媒体盒子", model: "Demo Media Box", brand: "示例品牌", room: "客厅", status: "idle", icon: "tv", control: "power", metrics: ["待机", "演示系统", "以太网"], actions: ["播放", "暂停", "打开应用", "开关"] },
  { id: "fridge-demo", name: "厨房冰箱", model: "Demo Fridge F1", brand: "示例品牌", room: "厨房", status: "online", icon: "fridge", control: "status", metrics: ["冷藏 4°C", "冷冻 -18°C", "门 已关闭"], actions: ["温度", "门状态", "模式", "告警"] },
  { id: "cleaner-demo", name: "扫地机器人", model: "Demo Cleaner C1", brand: "示例品牌", room: "客厅", status: "busy", icon: "robot", control: "robot", metrics: ["清扫中 68%", "电量 74%", "剩余 23 分钟"], actions: ["全屋清洁", "预约任务", "指定范围", "查看地图"] },
  { id: "aquarium-demo", name: "餐厅鱼缸", model: "Demo Aquarium A1", brand: "示例品牌", room: "餐厅", status: "warning", icon: "fish", control: "aquarium", metrics: ["水温 26.4°C", "滤芯 12%", "灯光 自动"], actions: ["喂食", "灯光", "水温", "滤芯状态"] },
  { id: "curtain-demo", name: "主卧窗帘", model: "Demo Curtain C2", brand: "示例品牌", room: "主卧", status: "online", icon: "curtain", control: "split-curtain", metrics: ["左帘 35%", "右帘 35%", "电机 正常"], actions: ["开合位置", "读取位置", "日程"] },
  { id: "plug-network-demo", name: "网络设备插座", model: "Demo Plug P1", brand: "示例品牌", room: "主卧", status: "online", icon: "plug", control: "energy", risk: "high", metrics: ["今日 0.19 kWh", "本周 1.32 kWh", "本月 5.48 kWh"], actions: ["开关", "查看用电", "重新上电"], capabilities: { "开关": { capabilityId: "power.set", write: true, risk: "high" }, "查看用电": { capabilityId: "energy.read", write: false, risk: "normal" }, "重新上电": { capabilityId: "power.cycle", write: true, risk: "high" } } },
  { id: "plug-server-demo", name: "服务器计量插座", model: "Demo Plug P2", brand: "示例品牌", room: "书房", status: "online", icon: "plug", control: "energy", metrics: ["今日 1.04 kWh", "本周 7.12 kWh", "本月 31.6 kWh"], actions: ["开关", "查看用电", "过载保护"] },
  { id: "speaker-demo", name: "客厅音箱", model: "Demo Speaker S1", brand: "示例品牌", room: "客厅", status: "idle", icon: "speaker", control: "voice", metrics: ["待机", "音量 28%", "在线"], actions: ["播放", "音量", "播报"] },
  { id: "hanger-demo", name: "阳台升降衣架", model: "Demo Hanger H1", brand: "示例品牌", room: "阳台", status: "online", icon: "hanger", control: "voice", metrics: ["高度 100%", "照明 关闭", "烘干 关闭"], actions: ["高度", "照明", "烘干"] },
  { id: "laptop-demo", name: "示例笔记本", model: "Demo Laptop L1", brand: "示例品牌", room: "书房", status: "online", icon: "apple", control: "presence", metrics: ["电量 82%", "Wi-Fi", "已解锁"], actions: ["在家状态", "电量", "通知"] },
  { id: "phone-a-demo", name: "示例手机 A", model: "Demo Phone A", brand: "示例品牌", room: "主卧", status: "online", icon: "phone", control: "presence", metrics: ["电量 69%", "Wi-Fi", "在家"], actions: ["在家状态", "电量", "通知"] },
  { id: "tablet-a-demo", name: "示例平板 A", model: "Demo Tablet A", brand: "示例品牌", room: "客厅", status: "online", icon: "apple", control: "presence", metrics: ["电量 91%", "Wi-Fi", "闲置"], actions: ["在家状态", "电量", "投屏"] },
  { id: "tablet-b-demo", name: "示例平板 B", model: "Demo Tablet B", brand: "示例品牌", room: "书房", status: "offline", icon: "apple", control: "presence", metrics: ["离线 2 小时", "书房", "—"], actions: ["在家状态", "电量", "投屏"] },
  { id: "phone-b-demo", name: "示例手机 B", model: "Demo Phone B", brand: "示例品牌", room: "次卧", status: "online", icon: "phone", control: "presence", metrics: ["电量 54%", "Wi-Fi", "在家"], actions: ["在家状态", "电量", "通知"] },
  { id: "fold-demo", name: "示例折叠屏", model: "Demo Fold F1", brand: "示例品牌", room: "主卧", status: "online", icon: "phone", control: "presence", metrics: ["电量 76%", "Wi-Fi", "在家"], actions: ["在家状态", "电量", "通知"] },
];

const initialTasks: Task[] = [
  { id: "task-101", title: "全屋地面清扫", device: "扫地机器人", status: "running", queue: "normal", transport: "async", realtime: false, progress: 68, time: "14:32" },
  { id: "task-102", title: "家庭照片增量备份", device: "示例数据中心", status: "running", queue: "normal", transport: "async", realtime: false, progress: 42, time: "14:18" },
  { id: "task-103", title: "关闭主卧窗帘", device: "主卧窗帘", status: "running", queue: "priority", transport: "async", realtime: true, progress: 46, time: "刚刚" },
  { id: "task-104", title: "晚间网络巡检", device: "示例智能中枢", status: "queued", queue: "normal", transport: "async", realtime: false, progress: 0, time: "22:00" },
  { id: "task-105", title: "演示失败任务", device: "示例数据中心", status: "failed", queue: "normal", transport: "async", realtime: false, progress: 36, time: "13:55" },
];

const deviceProfiles: DeviceProfile[] = [
  { id: "climate", name: "空调", description: "精确温控与模式", icon: "climate", control: "climate", defaultMetrics: ["目标 23°C", "室温 25°C", "自动模式"] },
  { id: "light", name: "可调节灯", description: "开关与亮度调节", icon: "light", control: "dimmable-light", defaultMetrics: ["亮度 62%", "暖白光", "在线"] },
  { id: "split-curtain", name: "左右窗帘", description: "双帘同步开合", icon: "curtain", control: "split-curtain", defaultMetrics: ["左帘 0%", "右帘 0%", "电机正常"] },
  { id: "roller-curtain", name: "卷帘 / 垂帘", description: "纵向单帘开合", icon: "roller", control: "roller-curtain", defaultMetrics: ["关闭 58%", "电机正常", "在线"] },
  { id: "aquarium", name: "智能鱼缸", description: "灯光、投食与水温", icon: "fish", control: "aquarium", defaultMetrics: ["水温 26.4°C", "滤芯 100%", "灯光自动"] },
  { id: "switch", name: "智能开关", description: "电源与能耗统计", icon: "plug", control: "energy", defaultMetrics: ["今日 0 kWh", "本周 0 kWh", "本月 0 kWh"] },
  { id: "router", name: "路由器", description: "网络状态与安全重启", icon: "router", control: "router", defaultMetrics: ["延迟 —", "客户端 0", "待配置"] },
  { id: "robot", name: "扫地机器人", description: "全屋清洁快捷入口", icon: "robot", control: "robot", defaultMetrics: ["待机", "电量 —", "地图待同步"] },
  { id: "voice", name: "语音设备", description: "长按说话下发指令", icon: "speaker", control: "voice", defaultMetrics: ["待机", "音量 30%", "在线"] },
  { id: "presence", name: "手机 / 平板 / 电脑", description: "只显示在线与离线", icon: "phone", control: "presence", defaultMetrics: ["电量 —", "网络待配置", "位置未知"] },
  { id: "hub", name: "家庭智能中枢", description: "Agent与Token用量", icon: "hub", control: "hub-usage", defaultMetrics: ["5 小时剩余 —", "每周剩余 —", "余额 —"] },
  { id: "server", name: "家庭数据中心", description: "服务与资源监控", icon: "nas", control: "server-health", defaultMetrics: ["服务 0/0", "CPU — · 内存 —", "存储 —"] },
];

const actionOptions: Record<DeviceControl, string[]> = {
  power: ["打开", "关闭", "切换信号源"],
  router: ["检查网络", "安全重启", "开启访客网络"],
  robot: ["全屋清洁"],
  aquarium: ["打开灯光", "关闭灯光", "投食一次"],
  "split-curtain": ["打开", "暂停", "关闭"],
  "roller-curtain": ["打开", "暂停", "关闭"],
  climate: ["打开", "关闭", "设置温度"],
  "dimmable-light": ["打开", "关闭", "调暗", "调亮"],
  energy: ["打开", "关闭", "读取用电量"],
  voice: ["播放语音", "停止播放", "设置音量"],
  presence: ["读取在线状态", "发送通知"],
  "hub-usage": ["调用 Agent", "执行 MCP 工具", "生成推荐"],
  "server-health": ["查询新下载电影", "检索电影", "执行备份"],
  status: ["读取状态"],
};

function capabilityCommand(device: Device, input: CapabilityCommandInput): CapabilityCommand {
  const write = input.write ?? true;
  return {
    ...input,
    write,
    risk: input.risk ?? (write && device.risk === "high" ? "high" : "normal"),
    parameters: input.parameters ?? {},
  };
}

function commandForAction(device: Device, action: string, options: Partial<CapabilityCommandInput> = {}): CapabilityCommand {
  const registered = device.capabilities?.[action];
  return capabilityCommand(device, {
    capabilityId: options.capabilityId ?? registered?.capabilityId ?? "device.action.invoke",
    label: options.label ?? action,
    parameters: options.parameters ?? { action },
    write: options.write ?? registered?.write,
    risk: options.risk ?? registered?.risk,
    queue: options.queue,
    realtime: options.realtime,
    duration: options.duration,
    outcome: options.outcome,
  });
}

const demoAgentActions = {
  "cleaner.start_all": { deviceId: "cleaner-demo", action: "全屋清洁", queue: "normal" as TaskQueue },
  "curtain.open": { deviceId: "curtain-demo", action: "打开窗帘", queue: "priority" as TaskQueue },
  "curtain.close": { deviceId: "curtain-demo", action: "关闭窗帘", queue: "priority" as TaskQueue },
  "data.run_backup": { deviceId: "data-demo", action: "执行演示备份", queue: "normal" as TaskQueue },
};

const roomNodes: Record<string, { left: string; top: string }> = {
  "display-demo": { left: "19%", top: "23%" },
  "media-demo": { left: "29%", top: "23%" },
  "cleaner-demo": { left: "27%", top: "50%" },
  "speaker-demo": { left: "15%", top: "49%" },
  "fridge-demo": { left: "74%", top: "24%" },
  "aquarium-demo": { left: "57%", top: "34%" },
  "curtain-demo": { left: "25%", top: "79%" },
  "router-mesh-demo": { left: "38%", top: "83%" },
  "plug-network-demo": { left: "15%", top: "84%" },
  "hub-demo": { left: "78%", top: "64%" },
  "data-demo": { left: "88%", top: "65%" },
  "plug-server-demo": { left: "83%", top: "80%" },
  "hanger-demo": { left: "56%", top: "83%" },
  "router-core-demo": { left: "45%", top: "51%" },
};

const statusLabel: Record<DeviceStatus, string> = {
  online: "在线",
  busy: "运行中",
  idle: "待机",
  offline: "离线",
  warning: "需关注",
};

const navItems = [
  { value: "overview", label: "设备总览", icon: LayoutDashboard },
  { value: "network", label: "网络拓扑", icon: Network },
  { value: "capability", label: "场景与流程", icon: GitBranch },
  { value: "tasks", label: "任务队列", icon: ListTodo },
];

const roomOrder = ["客厅", "主卧", "书房", "厨房", "餐厅", "阳台", "次卧"] as const;
const roomMeta: Record<(typeof roomOrder)[number], { icon: typeof Home; environment: string }> = {
  客厅: { icon: Tv, environment: "23.1°C · 56%" },
  主卧: { icon: PanelLeftClose, environment: "22.6°C · 54%" },
  书房: { icon: CircleGauge, environment: "23.4°C · 52%" },
  厨房: { icon: Refrigerator, environment: "24.0°C · 61%" },
  餐厅: { icon: Fish, environment: "23.3°C · 58%" },
  阳台: { icon: AirVent, environment: "21.8°C · 64%" },
  次卧: { icon: Smartphone, environment: "22.9°C · 55%" },
};

const sizeOrder: WidgetSize[] = ["compact", "standard", "wide", "large"];
const sizeLabels: Record<WidgetSize, string> = {
  compact: "1×1",
  standard: "2×1",
  wide: "4×1",
  large: "4×2",
};

function preferredWidgetSize(device: Device): WidgetSize {
  return ["power", "presence", "status"].includes(device.control) ? "compact" : "standard";
}

function DeviceIcon({ type, className = "size-5" }: { type: string; className?: string }) {
  const props = { className, strokeWidth: 1.8 };
  if (type === "hub") return <CircleGauge {...props} />;
  if (type === "nas") return <Server {...props} />;
  if (type === "router") return <Router {...props} />;
  if (type === "tv") return <Tv {...props} />;
  if (type === "fridge") return <Refrigerator {...props} />;
  if (type === "robot") return <Bot {...props} />;
  if (type === "fish") return <Fish {...props} />;
  if (type === "curtain") return <PanelLeftClose {...props} />;
  if (type === "roller") return <PanelTop {...props} />;
  if (type === "climate") return <AirVent {...props} />;
  if (type === "light") return <Lightbulb {...props} />;
  if (type === "plug") return <Zap {...props} />;
  if (type === "speaker") return <Speaker {...props} />;
  if (type === "hanger") return <AirVent {...props} />;
  if (type === "phone") return <Smartphone {...props} />;
  return <Smartphone {...props} />;
}

function CurtainOpenIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.5 4.5h5v15h-5zM15.5 4.5h5v15h-5zM10.5 12H6.5m0 0 2-2m-2 2 2 2M13.5 12h4m0 0-2-2m2 2-2 2" /></svg>;
}

function CurtainCloseIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 4.5h5.5v15H6zM12.5 4.5H18v15h-5.5zM3.5 12h3m0 0-2-2m2 2-2 2M20.5 12h-3m0 0 2-2m-2 2 2 2" /></svg>;
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`brand ${compact ? "brand-compact" : ""}`} aria-label="知微 Home Intelligence">
      <span className="brand-line" />
      <span>
        <strong>知微</strong>
        <em>Home Intelligence</em>
      </span>
    </div>
  );
}

function Widget({
  id,
  size,
  editing,
  onResize,
  className = "",
  children,
}: {
  id: string;
  size: WidgetSize;
  editing: boolean;
  onResize: (id: string) => void;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={`widget ${className}`} data-size={size}>
      {editing && (
        <button
          type="button"
          className="resize-control"
          onClick={() => onResize(id)}
          aria-label={`调整卡片尺寸，当前 ${sizeLabels[size]}`}
        >
          <Grip className="size-4" />
          {sizeLabels[size]}
        </button>
      )}
      {children}
    </section>
  );
}

function DeviceWidget({
  device,
  powered,
  editing,
  size,
  onResize,
  onSelect,
  onToggle,
  onAction,
}: {
  device: Device;
  powered: boolean;
  editing: boolean;
  size: WidgetSize;
  onResize: (id: string) => void;
  onSelect: (device: Device) => void;
  onToggle: (device: Device, next: boolean) => void;
  onAction: DispatchDeviceAction;
}) {
  const [curtainMode, setCurtainMode] = useState<"close" | "pause" | "open">("pause");
  const [curtainPosition, setCurtainPosition] = useState({ left: 35, right: 35 });
  const [curtainMoving, setCurtainMoving] = useState(false);
  const curtainOperation = useRef(0);
  const [rollerMode, setRollerMode] = useState<"close" | "pause" | "open">("pause");
  const [rollerPosition, setRollerPosition] = useState(58);
  const [rollerMoving, setRollerMoving] = useState(false);
  const rollerOperation = useRef(0);
  const [targetTemperature, setTargetTemperature] = useState(23);
  const [lightOn, setLightOn] = useState(true);
  const [brightness, setBrightness] = useState([62]);
  const [desiredBrightness, setDesiredBrightness] = useState([62]);
  const [fishLight, setFishLight] = useState("自然日光");
  const [fishLightOn, setFishLightOn] = useState(true);
  const [feeding, setFeeding] = useState(false);
  const [pendingControl, setPendingControl] = useState<string | null>(null);
  const [voiceActive, setVoiceActive] = useState(false);
  const voiceStartedAt = useRef(0);
  const voiceHolding = useRef(false);
  const isOffline = device.status === "offline";

  async function setCurtain(next: "close" | "pause" | "open") {
    if (isOffline) return;
    const operation = ++curtainOperation.current;
    setCurtainMode(next);
    if (next === "pause") {
      setCurtainMoving(false);
      await onAction(device, capabilityCommand(device, { capabilityId: "cover.stop", label: "暂停窗帘", parameters: { cover: "split" }, queue: "priority", realtime: true, duration: 700 }));
      return;
    }
    setCurtainMoving(true);
    const result = await onAction(device, capabilityCommand(device, { capabilityId: "cover.set_position", label: next === "open" ? "打开窗帘" : "关闭窗帘", parameters: { cover: "split", position: next === "open" ? 0 : 100 }, queue: "priority", realtime: true, duration: 2800 }));
    if (curtainOperation.current !== operation) return;
    if (result === "done") {
      setCurtainPosition(next === "open" ? { left: 0, right: 0 } : { left: 100, right: 100 });
    }
    setCurtainMoving(false);
    setCurtainMode("pause");
  }

  async function setRoller(next: "close" | "pause" | "open") {
    if (isOffline) return;
    const operation = ++rollerOperation.current;
    setRollerMode(next);
    if (next === "pause") {
      setRollerMoving(false);
      await onAction(device, capabilityCommand(device, { capabilityId: "cover.stop", label: "暂停卷帘", parameters: { cover: "roller" }, queue: "priority", realtime: true, duration: 700 }));
      return;
    }
    setRollerMoving(true);
    const result = await onAction(device, capabilityCommand(device, { capabilityId: "cover.set_position", label: next === "open" ? "打开卷帘" : "关闭卷帘", parameters: { cover: "roller", position: next === "open" ? 0 : 100 }, queue: "priority", realtime: true, duration: 2600 }));
    if (rollerOperation.current !== operation) return;
    if (result === "done") {
      setRollerPosition(next === "open" ? 0 : 100);
    }
    setRollerMoving(false);
    setRollerMode("pause");
  }

  async function feedFish() {
    if (feeding || isOffline) return;
    setFeeding(true);
    await onAction(device, capabilityCommand(device, { capabilityId: "aquarium.feed", label: "投食一次", parameters: { portions: 1 }, duration: 1800 }));
    setFeeding(false);
  }

  async function setTemperature(next: number) {
    if (pendingControl || isOffline) return;
    const bounded = Math.max(16, Math.min(30, next));
    setPendingControl("temperature");
    const result = await onAction(device, capabilityCommand(device, { capabilityId: "climate.set_temperature", label: `设置温度 ${bounded}°C`, parameters: { temperatureCelsius: bounded } }));
    if (result === "done") setTargetTemperature(bounded);
    setPendingControl(null);
  }

  async function setLightPower(next: boolean) {
    if (pendingControl || isOffline) return;
    setPendingControl("light-power");
    const result = await onAction(device, capabilityCommand(device, { capabilityId: "light.set_power", label: next ? "打开灯光" : "关闭灯光", parameters: { on: next } }));
    if (result === "done") setLightOn(next);
    setPendingControl(null);
  }

  async function commitBrightness(next: number[]) {
    if (pendingControl || isOffline) return;
    const value = next[0];
    setPendingControl("brightness");
    const result = await onAction(device, capabilityCommand(device, { capabilityId: "light.set_brightness", label: `设置亮度 ${value}%`, parameters: { brightnessPercent: value }, queue: "priority", realtime: true }));
    if (result === "done") setBrightness(next);
    else setDesiredBrightness(brightness);
    setPendingControl(null);
  }

  async function setAquariumLightMode(next: string) {
    if (pendingControl || isOffline) return;
    setPendingControl("aquarium-mode");
    const result = await onAction(device, capabilityCommand(device, { capabilityId: "aquarium.light.set_mode", label: `切换鱼缸灯光为${next}`, parameters: { mode: next } }));
    if (result === "done") setFishLight(next);
    setPendingControl(null);
  }

  async function setAquariumLightPower(next: boolean) {
    if (pendingControl || isOffline) return;
    setPendingControl("aquarium-power");
    const result = await onAction(device, capabilityCommand(device, { capabilityId: "aquarium.light.set_power", label: next ? "打开鱼缸灯光" : "关闭鱼缸灯光", parameters: { on: next } }));
    if (result === "done") setFishLightOn(next);
    setPendingControl(null);
  }

  function startVoice() {
    if (isOffline) return;
    voiceStartedAt.current = Date.now();
    voiceHolding.current = true;
    setVoiceActive(true);
  }

  function finishVoice() {
    if (!voiceHolding.current) return;
    const duration = Date.now() - voiceStartedAt.current;
    voiceHolding.current = false;
    setVoiceActive(false);
    if (duration >= 650) void onAction(device, capabilityCommand(device, { capabilityId: "voice.command", label: "语音指令", parameters: { input: "browser-microphone" } }));
    else toast("请按住说话", { description: "持续按住 0.6 秒后开始录入指令" });
  }

  const topControl = device.control === "power" || device.control === "energy"
    ? <Switch checked={powered} onCheckedChange={(next) => onToggle(device, next)} disabled={isOffline} aria-label={`${device.name}电源`} />
    : device.control === "presence"
      ? <span className={`presence-state ${device.status === "offline" ? "is-offline" : ""}`}><i/>{statusLabel[device.status]}</span>
      : device.control === "dimmable-light"
        ? <Switch checked={lightOn} onCheckedChange={(next) => void setLightPower(next)} disabled={isOffline || Boolean(pendingControl)} aria-label={`${device.name}灯光`} />
      : null;

  let control: ReactNode;
  if (device.control === "split-curtain") {
    control = (
      <div className="control-surface curtain-control">
        <div className={`icon-choice ${curtainMoving ? "is-moving" : ""}`} aria-label="窗帘控制">
          <button type="button" disabled={isOffline} className={curtainMode === "open" ? "active" : ""} onClick={() => setCurtain("open")} aria-label="打开窗帘"><CurtainOpenIcon/></button>
          <button type="button" disabled={isOffline} className={curtainMode === "pause" ? "active" : ""} onClick={() => setCurtain("pause")} aria-label="暂停窗帘"><Pause/></button>
          <button type="button" disabled={isOffline} className={curtainMode === "close" ? "active" : ""} onClick={() => setCurtain("close")} aria-label="关闭窗帘"><CurtainCloseIcon/></button>
        </div>
        <div className={`split-position ${curtainMoving ? "is-moving" : ""}`}>
          {curtainMoving ? <div className="motion-feedback"><LoaderCircle/><span>{curtainMode === "open" ? "正在打开" : "正在关闭"}</span><small>等待设备停止后读取真实位置</small></div> : <>
            <span>左帘<b>{curtainPosition.left}%</b><i style={{ width: `${curtainPosition.left}%` }}/></span>
            <span>右帘<b>{curtainPosition.right}%</b><i style={{ width: `${curtainPosition.right}%` }}/></span>
          </>}
        </div>
      </div>
    );
  } else if (device.control === "roller-curtain") {
    control = (
      <div className="control-surface roller-control device-roller-control">
        <div className="vertical-choice">
          <button type="button" disabled={isOffline} className={rollerMode === "open" ? "active" : ""} onClick={() => setRoller("open")} aria-label="打开卷帘"><ChevronsUp/></button>
          <button type="button" disabled={isOffline} className={rollerMode === "pause" ? "active" : ""} onClick={() => setRoller("pause")} aria-label="暂停卷帘"><Pause/></button>
          <button type="button" disabled={isOffline} className={rollerMode === "close" ? "active" : ""} onClick={() => setRoller("close")} aria-label="关闭卷帘"><ChevronsDown/></button>
        </div>
        {rollerMoving ? <div className="motion-feedback vertical"><LoaderCircle/><span>{rollerMode === "open" ? "正在打开" : "正在关闭"}</span><small>停止后同步真实位置</small></div> : <div className="roller-meter"><i><em style={{ height: `${rollerPosition}%` }}/></i><span><b>{rollerPosition}</b>%<small>关闭比例</small></span></div>}
      </div>
    );
  } else if (device.control === "climate") {
    control = <div className="temperature-stepper"><button type="button" disabled={isOffline || Boolean(pendingControl)} onClick={() => void setTemperature(targetTemperature - 1)} aria-label="温度减一度"><Minus/></button><span><b>{targetTemperature}</b><small>°C</small></span><button type="button" disabled={isOffline || Boolean(pendingControl)} onClick={() => void setTemperature(targetTemperature + 1)} aria-label="温度加一度"><Plus/></button></div>;
  } else if (device.control === "dimmable-light") {
    control = <div className={`device-light-control ${lightOn ? "is-on" : ""}`}><div className="light-summary"><Sun/><span>{lightOn ? "亮度" : "灯光已关闭"}</span><b>{lightOn ? `${desiredBrightness[0]}%` : "—"}</b></div>{lightOn && <Slider disabled={isOffline || Boolean(pendingControl)} value={desiredBrightness} onValueChange={setDesiredBrightness} onValueCommit={(next) => void commitBrightness(next)} aria-label="灯光亮度"/>}</div>;
  } else if (device.control === "aquarium") {
    control = (
      <div className="control-surface aquarium-control">
        <NativeSelect disabled={isOffline || Boolean(pendingControl)} value={fishLight} onChange={(event) => void setAquariumLightMode(event.target.value)} aria-label="鱼缸灯光类型">
          <NativeSelectOption value="自然日光">自然日光</NativeSelectOption>
          <NativeSelectOption value="水草生长">水草生长</NativeSelectOption>
          <NativeSelectOption value="月光观赏">月光观赏</NativeSelectOption>
        </NativeSelect>
        <button type="button" disabled={isOffline || Boolean(pendingControl)} className={`mini-action ${fishLightOn ? "active" : ""}`} onClick={() => void setAquariumLightPower(!fishLightOn)} aria-label="开关鱼缸灯"><Lightbulb/>{fishLightOn ? "灯已开" : "开灯"}</button>
        <button type="button" disabled={isOffline} className={`mini-action feed-action ${feeding ? "is-feeding" : ""}`} onClick={feedFish} aria-label="鱼缸投食">{feeding ? <LoaderCircle/> : <Fish/>}{feeding ? "投食中" : "投食"}</button>
      </div>
    );
  } else if (device.control === "energy") {
    control = (
      <div className="control-surface energy-control">
        {device.metrics.map((metric, index) => <span key={metric}><small>{["日", "周", "月"][index]}</small><b>{metric.replace(/^(今日|本周|本月)\s*/, "")}</b></span>)}
      </div>
    );
  } else if (device.control === "router") {
    control = (
      <div className="control-surface router-control">
        <span><b>{device.metrics[0]}</b><small>{device.metrics[1]}</small></span>
        <button type="button" disabled={isOffline} onClick={() => void onAction(device, capabilityCommand(device, { capabilityId: "network.restart", label: "安全重启", parameters: {}, risk: "high" }))}><RotateCw/>重启路由</button>
      </div>
    );
  } else if (device.control === "robot") {
    control = (
      <div className="control-surface robot-control">
        <span><b>{device.metrics[0]}</b><small>{device.metrics[1]}</small></span>
        <button type="button" disabled={isOffline} onClick={() => void onAction(device, capabilityCommand(device, { capabilityId: "vacuum.clean_all", label: "全屋清洁", parameters: {} }))}><Home/>全屋清洁</button>
      </div>
    );
  } else if (device.control === "voice") {
    control = (
      <button
        type="button"
        disabled={isOffline}
        className={`voice-hold ${voiceActive ? "is-listening" : ""}`}
        onPointerDown={startVoice}
        onPointerUp={finishVoice}
        onPointerCancel={finishVoice}
        onPointerLeave={finishVoice}
        onContextMenu={(event) => event.preventDefault()}
        aria-label={`按住向${device.name}说话`}
      >
        <span className="voice-orb"><Mic/></span>
        <span><strong>{voiceActive ? "正在聆听…" : "按住说话"}</strong><small>{voiceActive ? "松开发送指令" : "长按输入语音指令"}</small></span>
      </button>
    );
  } else if (device.control === "hub-usage") {
    control = (
      <div className="control-surface usage-control">
        <div><span>5 小时</span><b>72%</b><i><em style={{ width: "72%" }}/></i></div>
        <div><span>本周</span><b>84%</b><i><em style={{ width: "84%" }}/></i></div>
        <div className="token-balance"><span>预充值余额</span><b>¥128</b></div>
      </div>
    );
  } else if (device.control === "server-health") {
    control = (
      <div className="control-surface server-control">
        <div className="service-count"><span>运行服务</span><b>18<small>/18</small></b></div>
        {[{ label: "CPU", value: 21 }, { label: "内存", value: 48 }, { label: "存储", value: 61 }].map((item) => <div className="health-meter" key={item.label}><span>{item.label}</span><i><em style={{ width: `${item.value}%` }}/></i><b>{item.value}%</b></div>)}
      </div>
    );
  } else if (device.control === "presence") {
    control = <div className="presence-control"><span>{device.metrics[0]}</span><small>{device.status === "offline" ? "最后出现于 2 小时前" : "刚刚在家庭网络活跃"}</small></div>;
  } else {
    control = <div className="device-value">{device.metrics[0]}</div>;
  }

  return (
    <Widget id={device.id} size={size} editing={editing} onResize={onResize} className={`device-widget control-${device.control} ${isOffline ? "is-offline" : ""}`}>
      <div className="device-widget-top">
        <button type="button" className="device-title-button" onClick={() => onSelect(device)}>
          <span className={`device-icon tone-${device.status}`}><DeviceIcon type={device.icon} /></span>
          <span>
            <strong>{device.name}</strong>
            <small>{device.room} · {statusLabel[device.status]}</small>
          </span>
        </button>
        {topControl}
      </div>
      {control}
      {isOffline && <div className="offline-mask"><Wifi/><span>设备离线</span></div>}
    </Widget>
  );
}

function FloorPlan({ devices, onSelect }: { devices: Device[]; onSelect: (device: Device) => void }) {
  return (
    <div className="floor-layout">
      <div className="floor-canvas">
        <div className="floor-grid" aria-label="住宅一层设备分布图">
          <div className="room living"><span>客厅</span><small>5 个设备</small></div>
          <div className="room dining"><span>餐厅</span><small>1 个设备</small></div>
          <div className="room kitchen"><span>厨房</span><small>1 个设备</small></div>
          <div className="room study"><span>书房</span><small>5 个设备</small></div>
          <div className="room master"><span>主卧</span><small>4 个设备</small></div>
          <div className="room balcony"><span>阳台</span><small>1 个设备</small></div>
          <div className="room bedroom"><span>次卧</span><small>1 个设备</small></div>
          {devices.filter((device) => roomNodes[device.id]).map((device) => (
            <button
              key={device.id}
              type="button"
              className={`floor-device floor-device-${device.status}`}
              style={roomNodes[device.id]}
              onClick={() => onSelect(device)}
              aria-label={`查看${device.name}`}
            >
              <DeviceIcon type={device.icon} className="size-4" />
              <span>{device.name}</span>
            </button>
          ))}
        </div>
      </div>
      <aside className="room-summary">
        <div className="room-summary-head"><span>示例空间</span><strong>120㎡</strong></div>
        {[['客厅', 5], ['主卧', 4], ['书房', 5], ['厨房', 1], ['餐厅', 1], ['阳台', 1], ['次卧', 1]].map(([room, count]) => (
          <div className="room-summary-row" key={room}><span>{room}</span><span>{count} 台</span></div>
        ))}
      </aside>
    </div>
  );
}

function NetworkView({ devices, onSelect }: { devices: Device[]; onSelect: (device: Device) => void }) {
  const nodes = [
    { id: "router-main", x: 50, y: 15, label: "家庭主路由", value: "128 Mbps" },
    { id: "rpi-hub", x: 25, y: 48, label: "智能中枢", value: "12 项服务" },
    { id: "nas", x: 75, y: 48, label: "数据中心", value: "42 W" },
    { id: "router-bedroom", x: 15, y: 82, label: "主卧网络", value: "6 台设备" },
    { id: "tv-living", x: 50, y: 82, label: "影音设备", value: "3 台设备" },
    { id: "robot", x: 85, y: 82, label: "智能家居", value: "9 台设备" },
  ];
  return (
    <div className="network-view page-center-card">
      <svg className="network-lines" viewBox="0 0 1000 600" preserveAspectRatio="none" aria-hidden="true">
        <path d="M500 90 L250 290 M500 90 L750 290 M250 290 L150 492 M250 290 L500 492 M750 290 L850 492 M750 290 L500 492" />
      </svg>
      {nodes.map((node) => {
        const device = devices.find((item) => item.id === node.id)!;
        return (
          <button type="button" key={node.id} className="network-node" style={{ left: `${node.x}%`, top: `${node.y}%` }} onClick={() => onSelect(device)}>
            <span className="network-node-icon"><DeviceIcon type={device.icon} /></span>
            <span><strong>{node.label}</strong><small>{node.value}</small></span>
            <i className={`status-dot status-${device.status}`} />
          </button>
        );
      })}
    </div>
  );
}

function AutomationGrid({
  items,
  type,
  onEdit,
  onRun,
}: {
  items: AutomationItem[];
  type: "scene" | "workflow";
  onEdit: (type: "scene" | "workflow", item: AutomationItem) => void;
  onRun: (item: AutomationItem) => void;
}) {
  return <div className="automation-grid">{items.map((item) => {
    const Icon = item.icon;
    return <article className="automation-card" key={item.title}>
      <header><span className="automation-icon"><Icon/></span><div><strong>{item.title}</strong><small>{item.meta}</small></div><span className="automation-state">{item.state}</span></header>
      <div className="step-flow">{item.steps.map((step, index) => <div className="flow-step" key={step}><span>{index + 1}</span><b>{step}</b>{index < item.steps.length - 1 && <ChevronRight/>}</div>)}</div>
      <footer><button type="button" className="edit-flow-button" onClick={() => onEdit(type, item)}><Settings2/>编排</button><Button onClick={() => onRun(item)}><Play/>运行</Button></footer>
    </article>;
  })}</div>;
}

function CapabilityView({ devices, onDispatch }: { devices: Device[]; onDispatch: DispatchDeviceAction }) {
  const virtualDevices: Device[] = [
    { id: "planned-light-living", name: "客厅灯", model: "能力样例", brand: "待接入", room: "客厅", status: "online", icon: "light", control: "dimmable-light", metrics: ["亮度 62%"], actions: ["打开", "关闭", "调暗"] },
    { id: "planned-light-dining", name: "餐厅灯", model: "能力样例", brand: "待接入", room: "餐厅", status: "online", icon: "light", control: "dimmable-light", metrics: ["亮度 80%"], actions: ["打开", "关闭", "调暗"] },
  ];
  const planningDevices = [...devices, ...virtualDevices];
  const [composerOpen, setComposerOpen] = useState(false);
  const [composerType, setComposerType] = useState<"scene" | "workflow">("scene");
  const [intent, setIntent] = useState("");
  const [planSteps, setPlanSteps] = useState<PlanStep[]>([]);
  const [activeRun, setActiveRun] = useState<{ title: string; steps: PlanStep[] } | null>(null);
  const scenes: AutomationItem[] = [
    { title: "进入观影模式", icon: Tv, state: "可运行", meta: "上次运行 · 昨晚 21:08", steps: ["关闭窗帘", "调暗灯光", "打开显示屏", "启动流媒体盒子", "查询新电影", "语音推荐"] },
    { title: "离家模式", icon: Home, state: "可运行", meta: "上次运行 · 今天 08:42", steps: ["检查灯光", "关闭空调", "关闭新风", "关闭显示屏", "媒体盒子待机"] },
    { title: "夜间静谧", icon: CloudSun, state: "已预约", meta: "每天 · 23:20", steps: ["客厅灯 15%", "关闭窗帘", "播放白噪音", "开启门窗守护"] },
  ];
  const workflows: AutomationItem[] = [
    { title: "下载 4K 杜比视界电影", icon: Workflow, state: "需输入片名", meta: "媒体索引 · 下载器 · 消息通知", steps: ["解析片名", "检索资源", "筛选 4K DV", "提交下载", "等待完成", "发送通知"] },
    { title: "周末全屋维护", icon: Wrench, state: "草案", meta: "最近编辑 · 2 天前", steps: ["设备健康检查", "媒体库增量备份", "扫地清洁", "滤芯检查", "生成维护摘要"] },
    { title: "家庭网络恢复", icon: Router, state: "需确认", meta: "高风险动作受保护", steps: ["诊断外网", "检查主路由", "检查从路由", "生成重启计划", "人工确认", "逐节点恢复"] },
  ];

  function makeBinding(deviceName: string, action: string): StepBinding {
    const device = planningDevices.find((item) => item.name === deviceName) ?? planningDevices[0];
    return { id: `binding-${device.id}-${action}`, deviceId: device.id, deviceName: device.name, action };
  }

  function moviePlan(): PlanStep[] {
    return [
      { id: "movie-1", title: "关闭窗帘", status: "draft", bindings: [makeBinding("主卧窗帘", "关闭")] },
      { id: "movie-2", title: "调暗公共区域灯光", status: "draft", bindings: [makeBinding("客厅灯", "调暗"), makeBinding("餐厅灯", "关闭")] },
      { id: "movie-3", title: "打开显示屏", status: "draft", bindings: [makeBinding("客厅显示屏", "打开")] },
      { id: "movie-4", title: "启动播放器", status: "draft", bindings: [makeBinding("流媒体盒子", "打开播放器")] },
      { id: "movie-5", title: "查询并推荐新电影", status: "draft", bindings: [makeBinding("示例数据中心", "查询新下载电影并列出推荐")] },
      { id: "movie-6", title: "播放推荐语音", status: "draft", bindings: [makeBinding("客厅音箱", "播放推荐语音")] },
    ];
  }

  function planFromItem(item: { title: string; steps: string[] }): PlanStep[] {
    if (item.title === "进入观影模式") return moviePlan();
    const hub = devices.find((device) => device.id === "rpi-hub") ?? devices[0];
    return item.steps.map((step, index) => ({ id: `${item.title}-${index}`, title: step, status: "draft", bindings: [{ id: `binding-${item.title}-${index}`, deviceId: hub.id, deviceName: hub.name, action: step }] }));
  }

  function openComposer(type: "scene" | "workflow", item?: { title: string; steps: string[] }) {
    setComposerType(type);
    setIntent(item?.title ?? "");
    setPlanSteps(item ? planFromItem(item) : []);
    setComposerOpen(true);
  }

  function generateDraft() {
    if (/观影|电影模式/.test(intent)) setPlanSteps(moviePlan());
    else {
      const hub = devices.find((device) => device.id === "rpi-hub") ?? devices[0];
      setPlanSteps([
        { id: "draft-1", title: "理解意图并检查设备", status: "draft", bindings: [{ id: "binding-draft-1", deviceId: hub.id, deviceName: hub.name, action: "调用 Agent 解析意图" }] },
        { id: "draft-2", title: "执行主要设备动作", status: "draft", bindings: [{ id: "binding-draft-2", deviceId: hub.id, deviceName: hub.name, action: "执行 MCP 工具" }] },
        { id: "draft-3", title: "核对结果并通知", status: "draft", bindings: [{ id: "binding-draft-3", deviceId: hub.id, deviceName: hub.name, action: "生成执行摘要" }] },
      ]);
    }
  }

  function updateStep(stepId: string, patch: Partial<PlanStep>) {
    setPlanSteps((current) => current.map((step) => step.id === stepId ? { ...step, ...patch } : step));
  }

  function updateBinding(stepId: string, bindingId: string, patch: Partial<StepBinding>) {
    setPlanSteps((current) => current.map((step) => step.id === stepId ? { ...step, bindings: step.bindings.map((binding) => {
      if (binding.id !== bindingId) return binding;
      if (patch.deviceId) {
        const device = planningDevices.find((item) => item.id === patch.deviceId) ?? planningDevices[0];
        return { ...binding, deviceId: device.id, deviceName: device.name, action: actionOptions[device.control][0] };
      }
      return { ...binding, ...patch };
    }) } : step));
  }

  function addBinding(stepId: string) {
    const device = planningDevices[0];
    const binding: StepBinding = { id: `binding-${crypto.randomUUID()}`, deviceId: device.id, deviceName: device.name, action: actionOptions[device.control][0] };
    setPlanSteps((current) => current.map((step) => step.id === stepId ? { ...step, bindings: [...step.bindings, binding] } : step));
  }

  function removeBinding(stepId: string, bindingId: string) {
    setPlanSteps((current) => current.map((step) => step.id === stepId ? { ...step, bindings: step.bindings.filter((binding) => binding.id !== bindingId) } : step));
  }

  function addStep() {
    const device = planningDevices[0];
    setPlanSteps((current) => [...current, { id: `step-${crypto.randomUUID()}`, title: `步骤 ${current.length + 1}`, status: "draft", bindings: [{ id: `binding-${crypto.randomUUID()}`, deviceId: device.id, deviceName: device.name, action: actionOptions[device.control][0] }] }]);
  }

  async function startRun(title: string, sourceSteps: PlanStep[]) {
    const queuedSteps = sourceSteps.map((step) => ({ ...step, status: "queued" as const, result: undefined }));
    setActiveRun({ title, steps: queuedSteps });
    setComposerOpen(false);
    for (const step of queuedSteps) {
      setActiveRun((current) => current ? { ...current, steps: current.steps.map((item) => item.id === step.id ? { ...item, status: "running", result: undefined } : item) } : current);
      const results = await Promise.all(step.bindings.map((binding) => {
        const device = planningDevices.find((item) => item.id === binding.deviceId) ?? devices.find((item) => item.id === "rpi-hub") ?? devices[0];
        const realtime = ["split-curtain", "roller-curtain", "dimmable-light"].includes(device.control);
        return onDispatch(device, commandForAction(device, binding.action, { queue: realtime ? "priority" : "normal", realtime, duration: 1100 }));
      }));
      const failed = results.includes("failed");
      const cancelled = results.includes("cancelled");
      const stepStatus: PlanStepStatus = failed ? "failed" : cancelled ? "cancelled" : "success";
      const resultText = failed
        ? `${results.filter((result) => result === "failed").length} 个设备动作失败，流程已停止`
        : cancelled
          ? "设备动作已取消或未获高风险确认，流程已停止"
          : `${step.bindings.length} 个设备动作已确认完成`;
      setActiveRun((current) => current ? { ...current, steps: current.steps.map((item) => {
        if (item.id === step.id) return { ...item, status: stepStatus, result: resultText };
        if ((failed || cancelled) && item.status === "queued") return { ...item, status: "skipped", result: "因前序步骤未完成而跳过" };
        return item;
      }) } : current);
      if (failed || cancelled) break;
    }
  }

  return (
    <div className="capability-page">
      {activeRun && <section className="execution-plan">
        <header><div><span>EXECUTION PLAN</span><h2>{activeRun.title}</h2></div><div className="run-legend"><span><i className="running"/>执行中</span><span><i className="success"/>已完成</span></div></header>
        <div className="execution-steps">{activeRun.steps.map((step, index) => <article className={`execution-step status-${step.status}`} key={step.id}><div className="execution-index">{step.status === "success" ? <Check/> : step.status === "running" ? <LoaderCircle/> : index + 1}</div><div><strong>{step.title}</strong><small>{step.bindings.map((binding) => `${binding.deviceName} · ${binding.action}`).join(" ｜ ")}</small>{step.result && <p>{step.result}</p>}</div><span>{step.status === "success" ? "成功" : step.status === "running" ? "执行中" : step.status === "failed" ? "失败" : step.status === "cancelled" ? "已取消" : step.status === "skipped" ? "已跳过" : "等待"}</span></article>)}</div>
      </section>}
      <Tabs defaultValue="scenes" className="automation-tabs">
        <div className="automation-toolbar">
          <TabsList><TabsTrigger value="scenes"><Home/>家庭场景</TabsTrigger><TabsTrigger value="workflows"><Workflow/>工作流 / 家务流</TabsTrigger></TabsList>
          <Button variant="outline" onClick={() => openComposer("scene")}><Plus/>新建编排</Button>
        </div>
        <TabsContent value="scenes"><AutomationGrid items={scenes} type="scene" onEdit={openComposer} onRun={(item) => startRun(item.title, planFromItem(item))}/></TabsContent>
        <TabsContent value="workflows"><AutomationGrid items={workflows} type="workflow" onEdit={openComposer} onRun={(item) => startRun(item.title, planFromItem(item))}/></TabsContent>
      </Tabs>

      <Dialog open={composerOpen} onOpenChange={setComposerOpen}>
        <DialogContent className="composer-dialog plan-composer-dialog sm:max-w-[860px]">
          <DialogHeader><DialogTitle>{composerType === "scene" ? "Plan Mode · 家庭场景" : "Plan Mode · 工作流 / 家务流"}</DialogTitle><DialogDescription>一个卡片代表一个顺序步骤；每张卡片可以包含一个或多个并行执行的设备动作。</DialogDescription></DialogHeader>
          <div className="composer-body">
            <Label htmlFor="automation-intent">自然语言指令</Label>
            <div className="intent-row"><Textarea id="automation-intent" value={intent} onChange={(event) => setIntent(event.target.value)} placeholder={composerType === "scene" ? "例如：晚饭后自动切换到观影模式" : "例如：帮我下载某部电影的 4K 杜比视界版本"}/><Button disabled={!intent.trim()} onClick={generateDraft}><Cpu/>生成计划</Button></div>
            {planSteps.length > 0 && <div className="plan-card-list"><header><span><Cpu/>Agent 建议计划</span><b>等待 Review</b></header>{planSteps.map((step, index) => <article className="plan-edit-card" key={step.id}>
              <div className="plan-card-head"><span>{index + 1}</span><Input value={step.title} onChange={(event) => updateStep(step.id, { title: event.target.value })}/><button type="button" onClick={() => setPlanSteps((current) => current.filter((item) => item.id !== step.id))} aria-label="删除步骤"><Trash2/></button></div>
              <div className="binding-list">{step.bindings.map((binding) => {
                const device = planningDevices.find((item) => item.id === binding.deviceId) ?? planningDevices[0];
                return <div className="binding-row" key={binding.id}><span className="binding-type">DEVICE</span><NativeSelect value={binding.deviceId} onChange={(event) => updateBinding(step.id, binding.id, { deviceId: event.target.value })}>{planningDevices.map((item) => <NativeSelectOption value={item.id} key={item.id}>{item.name}</NativeSelectOption>)}</NativeSelect><span className="binding-arrow"><ArrowUpRight/></span><span className="binding-type">ACTION</span><NativeSelect value={binding.action} onChange={(event) => updateBinding(step.id, binding.id, { action: event.target.value })}>{Array.from(new Set([...actionOptions[device.control], binding.action])).map((action) => <NativeSelectOption value={action} key={action}>{action}</NativeSelectOption>)}</NativeSelect><button type="button" onClick={() => removeBinding(step.id, binding.id)} disabled={step.bindings.length === 1} aria-label="移除设备动作"><Trash2/></button></div>;
              })}</div>
              <button type="button" className="add-binding-button" onClick={() => addBinding(step.id)}><Plus/>添加设备动作</button>
            </article>)}<button type="button" className="add-step-button" onClick={addStep}><Plus/>添加执行卡片</button></div>}
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setComposerOpen(false)}>取消</Button><Button disabled={!planSteps.length} onClick={() => startRun(intent || "未命名计划", planSteps)}><Play/>批准并运行计划</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function QueuePanel({ queue, items, onRetry, onCancel }: { queue: TaskQueue; items: Task[]; onRetry: (task: Task) => void; onCancel: (task: Task) => void }) {
  const priority = queue === "priority";
  return <section className={`queue-panel ${priority ? "priority-queue" : "normal-queue"}`}>
    <header className="queue-head"><span className="queue-icon">{priority ? <Activity/> : <ListTodo/>}</span><div><h2>{priority ? "优先队列" : "普通队列"}</h2><p>{priority ? "仅接收异步任务，并持续上报设备状态" : "后台异步执行，适合清扫、备份与巡检"}</p></div><b>{items.filter((task) => !["done", "cancelled"].includes(task.status)).length}</b></header>
    <div className="queue-list">{items.length ? items.map((task) => (
      <div className="queue-task" key={task.id}>
        <span className={`task-state task-state-${task.status}`}>{task.status === "running" ? <LoaderCircle/> : task.status === "done" ? <Check/> : <Clock3/>}</span>
        <div className="task-copy"><strong>{task.title}</strong><small>{task.device} · {task.time}</small><div className="task-contract"><span>异步</span>{task.realtime && <span className="is-live"><i/>状态上报</span>}</div></div>
        <span className="task-status">{task.status === "running" ? "执行中" : task.status === "done" ? "已完成" : task.status === "failed" ? "失败" : task.status === "cancelled" ? "已取消" : "等待中"}</span>
        <div className="task-progress"><Progress value={task.progress}/><span>{task.progress}%</span></div>
        <div className="task-actions">
          {task.status === "failed" && <button type="button" onClick={() => onRetry(task)}><RotateCw/>重试</button>}
          {(task.status === "queued" || task.status === "running") && <button type="button" onClick={() => onCancel(task)}><Trash2/>取消</button>}
          {task.status === "cancelled" && <span>已取消</span>}
        </div>
      </div>
    )) : <div className="queue-empty"><Check/><span>当前队列为空</span></div>}</div>
  </section>;
}

function TaskView({ tasks, onCreate, onRetry, onCancel }: { tasks: Task[]; onCreate: () => void; onRetry: (task: Task) => void; onCancel: (task: Task) => void }) {
  const priorityTasks = tasks.filter((task) => task.queue === "priority");
  const normalTasks = tasks.filter((task) => task.queue === "normal");
  const active = tasks.filter((task) => task.status === "running").length;
  const waiting = tasks.filter((task) => task.status === "queued").length;
  const done = tasks.filter((task) => task.status === "done").length;

  return (
    <div className="task-page">
      <div className="task-stats queue-stats">
        <div><span>进行中</span><strong>{active}</strong></div>
        <div><span>等待中</span><strong>{waiting}</strong></div>
        <div><span>本次完成</span><strong>{done}</strong></div>
        <Button onClick={onCreate}><Plus/>新建任务</Button>
      </div>
      <div className="queue-layout"><QueuePanel queue="priority" items={priorityTasks} onRetry={onRetry} onCancel={onCancel}/><QueuePanel queue="normal" items={normalTasks} onRetry={onRetry} onCancel={onCancel}/></div>
    </div>
  );
}

export default function HomePage() {
  const [activeView, setActiveView] = useState("overview");
  const [overviewMode, setOverviewMode] = useState<"widgets" | "floor">("widgets");
  const [devices, setDevices] = useState<Device[]>(initialDevices);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [highRiskConfirmation, setHighRiskConfirmation] = useState<{ device: Device; action: string } | null>(null);
  const [addDeviceOpen, setAddDeviceOpen] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState<DeviceProfile | null>(null);
  const [newDeviceName, setNewDeviceName] = useState("");
  const [newDeviceRoom, setNewDeviceRoom] = useState<string>("客厅");
  const [newDeviceModel, setNewDeviceModel] = useState("");
  const [editingDevice, setEditingDevice] = useState(false);
  const [editName, setEditName] = useState("");
  const [editRoom, setEditRoom] = useState("");
  const [editIp, setEditIp] = useState("");
  const [editing, setEditing] = useState(false);
  const [tasks, setTasks] = useState<Task[]>(initialTasks);
  const [temperature] = useState(23);
  const [scene, setScene] = useState("在家");
  const [powered, setPowered] = useState<Record<string, boolean>>(() => Object.fromEntries(initialDevices.map((device) => [device.id, device.status !== "offline"])));
  const [sizes, setSizes] = useState<Record<string, WidgetSize>>(() => Object.fromEntries(initialDevices.map((device) => [device.id, preferredWidgetSize(device)])));
  const tasksRef = useRef(tasks);
  const taskRuntimes = useRef(new Map<string, TaskRuntime>());
  const confirmationQueue = useRef<ConfirmationRequest[]>([]);
  const activeConfirmation = useRef<ConfirmationRequest | null>(null);
  const requestDeviceActionRef = useRef<DispatchDeviceAction | null>(null);
  const onlineCount = devices.filter((device) => device.status !== "offline").length;

  useEffect(() => {
    tasksRef.current = tasks;
  }, [tasks]);

  function cycleSize(id: string) {
    setSizes((current) => {
      const currentSize = current[id] ?? "standard";
      const next = sizeOrder[(sizeOrder.indexOf(currentSize) + 1) % sizeOrder.length];
      return { ...current, [id]: next };
    });
  }

  function navigate(view: string) {
    setActiveView(view);
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  function selectDevice(device: Device) {
    setSelectedDevice(device);
    setEditName(device.name);
    setEditRoom(device.room);
    setEditIp(device.ip ?? "");
    setEditingDevice(false);
  }

  function runTask(taskId: string, queue: TaskQueue, duration: number, outcome: "done" | "failed"): Promise<TaskTerminalStatus> {
    return new Promise((resolve) => {
      const runtime: TaskRuntime = {
        startTimer: window.setTimeout(() => {
          if (runtime.settled) return;
          setTasks((current) => current.map((task) => task.id === taskId && task.status === "queued" ? { ...task, status: "running", progress: queue === "priority" ? 9 : 4 } : task));
          const startedAt = Date.now();
          runtime.ticker = window.setInterval(() => {
            if (runtime.settled) return;
            const progress = Math.min(100, Math.round(((Date.now() - startedAt) / duration) * 100));
            const status = progress >= 100 ? outcome : "running";
            setTasks((current) => current.map((task) => task.id === taskId ? { ...task, progress, status } : task));
            if (progress >= 100) settleTask(taskId, outcome);
          }, queue === "priority" ? 180 : 420);
        }, queue === "priority" ? 120 : 520),
        settled: false,
        resolve,
      };
      taskRuntimes.current.set(taskId, runtime);
    });
  }

  function settleTask(taskId: string, status: TaskTerminalStatus) {
    const runtime = taskRuntimes.current.get(taskId);
    if (!runtime || runtime.settled) return;
    runtime.settled = true;
    window.clearTimeout(runtime.startTimer);
    if (runtime.ticker) window.clearInterval(runtime.ticker);
    taskRuntimes.current.delete(taskId);
    if (status === "cancelled") {
      setTasks((current) => current.map((task) => task.id === taskId ? { ...task, status, progress: task.progress } : task));
    }
    runtime.resolve(status);
  }

  async function dispatchTask(device: Device, command: CapabilityCommand): Promise<TaskTerminalStatus> {
    if (device.status === "offline") {
      toast.error("设备离线，未创建任务", { description: `${device.name} 仅保留状态查看` });
      return "failed";
    }
    const queue = command.queue ?? "normal";
    const realtime = queue === "priority" ? true : Boolean(command.realtime);
    const duration = command.duration ?? (queue === "priority" ? 2800 : 3800);
    const taskId = `task-${crypto.randomUUID()}`;
    const newTask: Task = {
      id: taskId,
      title: command.label,
      device: device.name,
      status: "queued",
      queue,
      transport: "async",
      realtime,
      progress: 0,
      time: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }),
      capabilityId: command.capabilityId,
      parameters: command.parameters,
      risk: command.risk,
    };
    setTasks((current) => [newTask, ...current]);
    toast.success(queue === "priority" ? "已进入优先队列" : "已进入普通队列", { description: `${device.name} · ${command.label}${realtime ? " · 状态实时上报" : ""}` });
    return runTask(taskId, queue, duration, command.outcome ?? "done");
  }

  function showNextConfirmation() {
    if (activeConfirmation.current || confirmationQueue.current.length === 0) return;
    const next = confirmationQueue.current.shift() ?? null;
    activeConfirmation.current = next;
    setHighRiskConfirmation(next ? { device: next.device, action: next.command.label } : null);
  }

  function requestConfirmation(device: Device, command: CapabilityCommand): Promise<boolean> {
    return new Promise((resolve) => {
      confirmationQueue.current.push({ id: `confirm-${crypto.randomUUID()}`, device, command, resolve });
      showNextConfirmation();
    });
  }

  function resolveConfirmation(confirmed: boolean) {
    const request = activeConfirmation.current;
    if (!request) return;
    activeConfirmation.current = null;
    setHighRiskConfirmation(null);
    request.resolve(confirmed);
    window.setTimeout(showNextConfirmation, 0);
  }

  function requiresConfirmation(command: CapabilityCommand) {
    return command.write && command.risk === "high";
  }

  async function requestDeviceAction(device: Device, command: CapabilityCommand): Promise<TaskTerminalStatus> {
    if (requiresConfirmation(command)) {
      const confirmed = await requestConfirmation(device, command);
      if (!confirmed) {
        toast("高风险动作已取消", { description: `${device.name} · ${command.label}` });
        return "cancelled";
      }
    }
    return dispatchTask(device, command);
  }

  async function toggleDevice(device: Device, next: boolean) {
    const status = await requestDeviceAction(device, capabilityCommand(device, { capabilityId: "power.set", label: next ? "开启设备" : "关闭设备", parameters: { on: next } }));
    if (status === "done") {
      setPowered((current) => ({ ...current, [device.id]: next }));
      toast.success("设备已确认状态", { description: `${device.name} · ${next ? "已开启" : "已关闭"}` });
    }
  }

  function cancelTask(task: Task) {
    settleTask(task.id, "cancelled");
    setTasks((current) => current.map((item) => item.id === task.id ? { ...item, status: "cancelled" } : item));
    toast("任务已取消", { description: `${task.device} · ${task.title}` });
  }

  function retryTask(task: Task) {
    setTasks((current) => current.map((item) => item.id === task.id ? { ...item, status: "queued", progress: 0, time: "刚刚" } : item));
    void runTask(task.id, task.queue, task.queue === "priority" ? 2800 : 3800, "done");
    toast.success("任务已重新排队", { description: `${task.device} · ${task.title}` });
  }

  function chooseProfile(profile: DeviceProfile) {
    setSelectedProfile(profile);
    setNewDeviceName(profile.name);
    setNewDeviceModel("");
  }

  function addDevice() {
    if (!selectedProfile || !newDeviceName.trim()) return;
    const id = `${selectedProfile.id}-${Date.now().toString().slice(-6)}`;
    const device: Device = {
      id,
      name: newDeviceName.trim(),
      model: newDeviceModel.trim() || "待配置型号",
      brand: "待配置品牌",
      room: newDeviceRoom,
      status: "online",
      icon: selectedProfile.icon,
      control: selectedProfile.control,
      metrics: selectedProfile.defaultMetrics,
      actions: ["查看状态", "编辑参数", "运行自检"],
      ip: "自动发现",
    };
    setDevices((current) => [...current, device]);
    setPowered((current) => ({ ...current, [id]: true }));
    setSizes((current) => ({ ...current, [id]: preferredWidgetSize(device) }));
    setAddDeviceOpen(false);
    setSelectedProfile(null);
    selectDevice(device);
    window.setTimeout(() => setEditingDevice(true), 0);
    toast.success("设备已添加", { description: `${device.name} · ${device.room} · 可继续配置 MCP 参数` });
  }

  function saveDevice() {
    if (!selectedDevice || !editName.trim()) return;
    const updated = { ...selectedDevice, name: editName.trim(), room: editRoom, ip: editIp.trim() || "自动发现" };
    setDevices((current) => current.map((device) => device.id === updated.id ? updated : device));
    setSelectedDevice(updated);
    setEditingDevice(false);
    toast.success("设备参数已保存", { description: `${updated.name} · 已归属到${updated.room}` });
  }

  useEffect(() => {
    requestDeviceActionRef.current = requestDeviceAction;
  });

  useEffect(() => {
    const context = (document as Document & { modelContext?: { registerTool: (tool: unknown, options?: { signal?: AbortSignal }) => void | Promise<void> } }).modelContext;
    if (!context?.registerTool) return;
    const lifecycle = new AbortController();
    const register = async () => {
      await context.registerTool({
        name: "read_home_status",
        title: "读取家庭状态",
        description: "读取公开原型中的虚构设备、环境和任务摘要。",
        inputSchema: { type: "object", properties: {}, additionalProperties: false },
        annotations: { readOnlyHint: true, untrustedContentHint: false },
        execute: () => ({ devices: devices.length, reachable: onlineCount, temperature, activeTasks: tasksRef.current.filter((task) => task.status === "running").length }),
      }, { signal: lifecycle.signal });
      await context.registerTool({
        name: "dispatch_device_task",
        title: "创建演示任务",
        description: "仅在浏览器内为虚构设备创建演示队列项，不连接或控制真实设备。",
        inputSchema: { type: "object", properties: { capabilityId: { type: "string", enum: Object.keys(demoAgentActions) } }, required: ["capabilityId"], additionalProperties: false },
        annotations: { readOnlyHint: false, untrustedContentHint: false },
        execute: async (input: unknown) => {
          const payload = input as { capabilityId?: keyof typeof demoAgentActions };
          const allowed = payload.capabilityId ? demoAgentActions[payload.capabilityId] : undefined;
          const device = allowed ? devices.find((item) => item.id === allowed.deviceId) : undefined;
          if (!allowed || !device || device.status === "offline") throw new Error("演示能力不可用");
          const dispatcher = requestDeviceActionRef.current;
          if (!dispatcher) throw new Error("演示调度器尚未就绪");
          const status = await dispatcher(device, commandForAction(device, allowed.action, { capabilityId: String(payload.capabilityId), parameters: { source: "webmcp" }, queue: allowed.queue, realtime: allowed.queue === "priority" }));
          return { mock: true, terminalStatus: status, device: device.name, capabilityId: payload.capabilityId };
        },
      }, { signal: lifecycle.signal });
    };
    void register().catch(() => undefined);
    return () => lifecycle.abort();
  }, [devices, onlineCount, temperature]);

  const pageTitle = navItems.find((item) => item.value === activeView)?.label ?? "设备总览";
  return (
    <main className="app-root">
      <Toaster position="top-center" richColors />
      <div className="app-shell">
        <aside className="sidebar">
        <Brand />
        <nav className="desktop-nav" aria-label="主导航">
          {navItems.map((item) => (
            <button type="button" key={item.value} className={activeView === item.value ? "active" : ""} onClick={() => navigate(item.value)}>
              <item.icon className="size-5" />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-home">
          <div><span className="presence-dot"/><strong>家中</strong></div>
          <span>{onlineCount} 台在线</span>
        </div>
        <div className="sidebar-signature">
          <span>见微知著<br/>万物留声</span>
          <small>© 2026 知微<br/>Home Intelligence</small>
        </div>
        </aside>

        <div className="workspace">
        <header className="topbar">
          <div className="mobile-brand"><Brand compact /></div>
          <button type="button" className="home-select"><Home className="size-4"/><span>当前住宅</span><ChevronDown className="size-4"/></button>
          <div className="topbar-spacer" />
          <div className="ambient-chip"><CloudSun className="size-4"/><span>23°C</span></div>
          <div className="ambient-chip desktop-only"><Droplets className="size-4"/><span>58%</span></div>
          <button type="button" className="icon-button" aria-label="设置"><Settings2 className="size-4"/></button>
        </header>

        <div className="page-wrap">
          <div className="page-heading">
            <div><span className="page-kicker">SATURDAY · 26 SEP</span><h1>{pageTitle}</h1></div>
            {activeView === "overview" && (
              <div className="overview-tools">
                <div className="segmented" aria-label="设备总览显示方式">
                  <button type="button" className={overviewMode === "widgets" ? "active" : ""} onClick={() => setOverviewMode("widgets")}><Grid2X2 className="size-4"/>卡片</button>
                  <button type="button" className={overviewMode === "floor" ? "active" : ""} onClick={() => setOverviewMode("floor")}><Map className="size-4"/>户型图</button>
                </div>
                {overviewMode === "widgets" && <button type="button" className={`layout-button ${editing ? "active" : ""}`} onClick={() => setEditing((value) => !value)}><Settings2 className="size-4"/>{editing ? "完成" : "编辑布局"}</button>}
                <Button className="add-device-button" onClick={() => { setSelectedProfile(null); setAddDeviceOpen(true); }}><Plus/>添加设备</Button>
              </div>
            )}
          </div>

          {activeView === "overview" && overviewMode === "widgets" && (
            <div>
              <div className="home-status-strip">
                <div className="status-pill"><Thermometer/><span>室内</span><strong>{temperature}°C</strong></div>
                <div className="status-pill"><Droplets/><span>湿度</span><strong>58%</strong></div>
                <button type="button" className="status-pill" onClick={() => setScene((current) => current === "在家" ? "静谧" : current === "静谧" ? "离家" : "在家")}><Home/><span>模式</span><strong>{scene}</strong></button>
                <div className="status-pill"><Wifi/><span>在线</span><strong>{onlineCount}/{devices.length}</strong></div>
                <div className="status-pill"><Zap/><span>用电</span><strong>6.8 kWh</strong></div>
                <button type="button" className="status-pill" onClick={() => navigate("tasks")}><ListTodo/><span>任务</span><strong>{tasks.filter((task) => task.status === "running").length} 项</strong></button>
              </div>

              <div className={`room-dashboard ${editing ? "is-editing" : ""}`}>
                {roomOrder.map((room) => {
                  const roomDevices = devices.filter((device) => device.room === room);
                  const RoomIcon = roomMeta[room].icon;
                  return (
                    <section className="room-section" key={room}>
                      <header className="room-section-head">
                        <div><RoomIcon/><h2>{room}</h2></div>
                        <span>{roomMeta[room].environment}<b>{roomDevices.length} 台</b></span>
                      </header>
                      <div className="room-device-grid">
                        {roomDevices.map((device) => (
                          <DeviceWidget key={device.id} device={device} powered={powered[device.id]} editing={editing} size={sizes[device.id] ?? preferredWidgetSize(device)} onResize={cycleSize} onSelect={selectDevice} onToggle={toggleDevice} onAction={requestDeviceAction} />
                        ))}
                      </div>
                    </section>
                  );
                })}
              </div>
            </div>
          )}

          {activeView === "overview" && overviewMode === "floor" && <FloorPlan devices={devices} onSelect={selectDevice} />}
          {activeView === "network" && <NetworkView devices={devices} onSelect={selectDevice} />}
          {activeView === "capability" && <CapabilityView devices={devices} onDispatch={requestDeviceAction} />}
          {activeView === "tasks" && <TaskView tasks={tasks} onCreate={() => void requestDeviceAction(devices[0], commandForAction(devices[0], "全屋设备巡检", { capabilityId: "home.inspect" }))} onRetry={retryTask} onCancel={cancelTask} />}

        </div>
        </div>
      </div>

      <nav className="mobile-nav" aria-label="移动端导航">
        {navItems.map((item) => <button type="button" key={item.value} className={activeView === item.value ? "active" : ""} onClick={() => navigate(item.value)}><item.icon/><span>{item.label}</span></button>)}
      </nav>

      <Sheet open={Boolean(selectedDevice)} onOpenChange={(open) => !open && setSelectedDevice(null)}>
        <SheetContent className="device-sheet w-[min(440px,94vw)] p-0 sm:max-w-[440px]">
          {selectedDevice && (
            <>
              <SheetHeader className="device-sheet-head">
                <div className="sheet-device-title"><span className={`device-icon tone-${selectedDevice.status}`}><DeviceIcon type={selectedDevice.icon}/></span><div><SheetTitle>{selectedDevice.name}</SheetTitle><SheetDescription>{selectedDevice.brand} · {selectedDevice.model}</SheetDescription></div></div>
                <div className="sheet-meta"><span className={`status-dot status-${selectedDevice.status}`}/>{statusLabel[selectedDevice.status]}<i/> {selectedDevice.room}<i/> {selectedDevice.ip ?? "自动发现"}</div>
              </SheetHeader>
              <div className="device-sheet-body">
                {editingDevice ? <div className="device-edit-form">
                  <div><Label htmlFor="edit-device-name">设备名称</Label><Input id="edit-device-name" value={editName} onChange={(event) => setEditName(event.target.value)}/></div>
                  <div><Label htmlFor="edit-device-room">物理空间归属</Label><NativeSelect id="edit-device-room" value={editRoom} onChange={(event) => setEditRoom(event.target.value)}>{roomOrder.map((room) => <NativeSelectOption value={room} key={room}>{room}</NativeSelectOption>)}</NativeSelect></div>
                  <div><Label htmlFor="edit-device-ip">局域网地址 / MCP Endpoint</Label><Input id="edit-device-ip" value={editIp} onChange={(event) => setEditIp(event.target.value)} placeholder="自动发现或手动填写"/></div>
                  <div className="edit-form-actions"><Button variant="outline" onClick={() => setEditingDevice(false)}>取消</Button><Button onClick={saveDevice}>保存参数</Button></div>
                </div> : <>
                  <div className="sheet-section"><span className="sheet-label">当前状态</span><div className="metric-grid">{selectedDevice.metrics.map((metric) => <div key={metric}>{metric}</div>)}</div></div>
                  {(selectedDevice.control === "power" || selectedDevice.control === "energy") && <div className="sheet-section"><span className="sheet-label">快速控制</span><div className="sheet-control"><span><strong>设备电源</strong><small>{powered[selectedDevice.id] ? "已开启" : "已关闭"}</small></span><Switch disabled={selectedDevice.status === "offline"} checked={powered[selectedDevice.id]} onCheckedChange={(next) => toggleDevice(selectedDevice, next)}/></div></div>}
                  <div className="sheet-section"><span className="sheet-label">可用操作</span><div className="action-grid">{selectedDevice.actions.map((action) => <button type="button" disabled={selectedDevice.status === "offline"} key={action} onClick={() => void requestDeviceAction(selectedDevice, commandForAction(selectedDevice, action))}>{action}<ChevronRight/></button>)}</div></div>
                  <div className="sheet-footer-actions"><Button variant="outline" onClick={() => setEditingDevice(true)}><Settings2/>编辑设备</Button><Button disabled={selectedDevice.status === "offline"} className="sheet-primary" onClick={() => void requestDeviceAction(selectedDevice, commandForAction(selectedDevice, "设备自检", { capabilityId: "device.self_test" }))}>运行设备自检<Play/></Button></div>
                </>}
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      <Dialog open={addDeviceOpen} onOpenChange={setAddDeviceOpen}>
        <DialogContent className="add-device-dialog sm:max-w-[900px]">
          <DialogHeader><DialogTitle>{selectedProfile ? "配置新设备" : "添加新设备"}</DialogTitle><DialogDescription>{selectedProfile ? `已选择“${selectedProfile.name}”能力模板，完成命名和空间归属后即可注册。` : "先选择设备能力模板。控件、状态字段和异步任务协议会自动匹配。"}</DialogDescription></DialogHeader>
          {!selectedProfile ? <div className="profile-grid">{deviceProfiles.map((profile) => <button type="button" className="profile-card" key={profile.id} onClick={() => chooseProfile(profile)}><span><DeviceIcon type={profile.icon}/></span><div><strong>{profile.name}</strong><small>{profile.description}</small></div><ChevronRight/></button>)}</div> : <div className="add-device-config">
            <div className="selected-profile-card"><span><DeviceIcon type={selectedProfile.icon}/></span><div><strong>{selectedProfile.name}</strong><small>{selectedProfile.description}</small></div><button type="button" onClick={() => setSelectedProfile(null)}>更换模板</button></div>
            <div className="config-grid">
              <div><Label htmlFor="new-device-name">设备名称</Label><Input id="new-device-name" value={newDeviceName} onChange={(event) => setNewDeviceName(event.target.value)}/></div>
              <div><Label htmlFor="new-device-room">物理空间归属</Label><NativeSelect id="new-device-room" value={newDeviceRoom} onChange={(event) => setNewDeviceRoom(event.target.value)}>{roomOrder.map((room) => <NativeSelectOption value={room} key={room}>{room}</NativeSelectOption>)}</NativeSelect></div>
              <div className="config-wide"><Label htmlFor="new-device-model">品牌 / 型号</Label><Input id="new-device-model" value={newDeviceModel} onChange={(event) => setNewDeviceModel(event.target.value)} placeholder="例如：Mijia Air Conditioner Pro"/></div>
            </div>
            <div className="profile-contract"><ShieldCheck/><span><strong>设备能力协议</strong><small>异步任务 · 状态上报 · MCP 工具映射将在详情页继续配置</small></span></div>
          </div>}
          <DialogFooter>{selectedProfile && <Button variant="outline" onClick={() => setSelectedProfile(null)}>上一步</Button>}<Button disabled={!selectedProfile || !newDeviceName.trim()} onClick={addDevice}><Plus/>添加并进入配置</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={Boolean(highRiskConfirmation)} onOpenChange={(open) => !open && resolveConfirmation(false)}>
        <AlertDialogContent className="restart-dialog" size="sm">
          <AlertDialogHeader>
            <AlertDialogMedia><ShieldCheck/></AlertDialogMedia>
            <AlertDialogTitle>确认{highRiskConfirmation?.action}？</AlertDialogTitle>
            <AlertDialogDescription>{highRiskConfirmation?.device.name} 的这个动作风险较高，可能使网络、自动化和状态上报暂时不可用。确认后才会创建异步任务，设备回执前不会提前改变状态。</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction className="restart-confirm" onClick={() => resolveConfirmation(true)}>确认执行</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </main>
  );
}
