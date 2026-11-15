using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using BepInEx;
using HarmonyLib;
using UnityEngine;
using System.Runtime.InteropServices;

[BepInPlugin("local.vanya.culttrainer", "Cult Trainer RU", "1.4.0")]
public class CultTrainer : BaseUnityPlugin {
    public static bool[] Flags = new bool[10];
    public static int Multiplier = 10;
    public static bool DlcUnlocked;
    bool dlcPending;
    MethodInfo dlcRefresh;
    static MethodInfo[] dlcChecks;
    static readonly string Root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "CultTrainerRU");
    float next; Harmony harmony; string error = ""; int patched; bool ready;
    readonly Dictionary<HealthPlayer, Health.CheatMode> originalGod = new Dictionary<HealthPlayer, Health.CheatMode>();
    bool wasFree; bool freeOwned;
    float nextQuests;
    volatile bool ioRunning;
    System.Threading.Thread ioThread;
    sealed class Command { public bool[] Flags; public int Multiplier; public bool Quests; public bool Live; public bool Dlc; }
    volatile Command incoming = new Command { Flags=new bool[10], Multiplier=10 };
    volatile string outgoingStatus="", outgoingQuests=null, outgoingResult=null, incomingQuest=null;
    string lastQuestSnapshot="";
    readonly Dictionary<string,string> titleCache = new Dictionary<string,string>();
    MethodInfo translator;
    static readonly int ProcessId = System.Diagnostics.Process.GetCurrentProcess().Id;
    double maxTickMs, totalTickMs; long tickCount;
    int showRequest;
    GUIStyle launcherStyle;
    float nextShow;
    [DllImport("user32.dll")] static extern bool AllowSetForegroundWindow(int processId);

    readonly string session = Guid.NewGuid().ToString("N");
    readonly DateTime started = DateTime.UtcNow;
    string lastQuestRequest = "";
    readonly Dictionary<ObjectivesData,string> questKeys = new Dictionary<ObjectivesData,string>();
    static readonly HashSet<ObjectivesData> forcedQuests = new HashSet<ObjectivesData>();
    void Awake() {
        Application.runInBackground = true;
        gameObject.hideFlags = HideFlags.HideAndDontSave;
        Directory.CreateDirectory(Root);
        Logger.LogInfo("IPC directory: " + Root);
        harmony = new Harmony("local.vanya.culttrainer");
        try {
            Patch(typeof(HealthPlayer), "DealDamage", "Damage");
            Patch(typeof(FaithAmmo), "UseAmmo", "Ammo");
            Patch(typeof(FaithAmmo), "CanAfford", "Afford");
            Patch(typeof(FollowerBrain), "MakeDissenter", "Dissent");
            Patch(typeof(FollowerBrain), "MakeSick", "Sick");
            Patch(typeof(PickUp), "PickMeUp", "Pickup", "PickupDone");
            foreach(var t in new[]{typeof(FollowerTask_Pray),typeof(FollowerTask_PrayPassive)})
                foreach(var m in t.GetMethods(BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static|BindingFlags.Instance).Where(m=>m.Name=="GetDurationPerDevotion"))
                    { harmony.Patch(m, prefix: new HarmonyMethod(typeof(CultTrainer), "Prayer")); patched++; }
            foreach(var name in new[]{"Satiation","Starvation","Rest","Exhaustion","Illness","Dissent","Faith"}) {
                foreach(var t in new[]{typeof(FollowerInfo),typeof(FollowerBrainStats)}) {
                    if(t.GetMethod("set_"+name)!=null) Patch(t,"set_"+name,"StatSet");
                }
            }
            Patch(typeof(CultFaithManager), "set_CurrentFaith", "FaithSet");
            Patch(typeof(ObjectivesData), "TryComplete", "ForceQuest");
            dlcChecks=typeof(GameManager).GetMethods(BindingFlags.Static|BindingFlags.Public|BindingFlags.NonPublic).Where(m=>m.Name.StartsWith("Authenticate") && m.Name.EndsWith("DLC") && m.ReturnType==typeof(bool) && m.GetParameters().Length==0).ToArray();
            if(dlcChecks.Length!=8)throw new Exception("DLC check layout changed; expected 8 methods.");
            foreach(var method in dlcChecks) {harmony.Patch(method,prefix:new HarmonyMethod(typeof(CultTrainer),"DlcAccess"));patched++;}
            dlcRefresh=AccessTools.Method(typeof(GameManager),"CheckDLCStatus");
            harmony.Patch(AccessTools.Method(typeof(SettingsManager),"ApplySettings"),postfix:new HarmonyMethod(typeof(CultTrainer),"Background"));patched++;
            var loc=AccessTools.TypeByName("I2.Loc.LocalizationManager");
            if(loc!=null)translator=loc.GetMethods().FirstOrDefault(m=>m.Name=="GetTranslation" && m.GetParameters().Length==8);
            SelfTest(); ready=true;
            Logger.LogInfo("Trainer ready: " + patched + " hooks, self-test PASS");
        } catch(Exception e) { error=e.ToString(); Logger.LogError(e); harmony.UnpatchSelf(); }
        ioRunning=true;
        ioThread=new System.Threading.Thread(IoLoop);ioThread.IsBackground=true;ioThread.Name="CultTrainer IPC";ioThread.Start();
    }
    void Patch(Type type,string name,string pre,string post=null) {
        var method=AccessTools.Method(type,name);
        if(method==null)throw new MissingMethodException(type.Name,name);
        harmony.Patch(method, prefix:new HarmonyMethod(typeof(CultTrainer),pre), postfix:post==null?null:new HarmonyMethod(typeof(CultTrainer),post)); patched++;
    }
    static void SelfTest() {
        // Exercise the actual patched game setters without touching a save or live follower.
        var info=(FollowerInfo)System.Runtime.Serialization.FormatterServices.GetUninitializedObject(typeof(FollowerInfo));
        for(int i=0;i<Flags.Length;i++)Flags[i]=true;
        info.Satiation=1; info.Starvation=80; info.Rest=2; info.Illness=90; info.Dissent=90; info.Faith=1;
        if(info.Satiation!=100 || info.Starvation!=0 || info.Rest!=100 || info.Illness!=0 || info.Dissent!=0 || info.Faith!=100)throw new Exception("Follower hook self-test failed");
        Array.Clear(Flags,0,Flags.Length);
        info.Satiation=23; info.Illness=17;
        if(info.Satiation!=23 || info.Illness!=17)throw new Exception("Hook disable self-test failed");
        DlcUnlocked=true;
        try {foreach(var method in dlcChecks)if(!(bool)method.Invoke(null,null))throw new Exception("DLC hook self-test failed: "+method.Name);}
        finally {DlcUnlocked=false;}
    }
    void Update() {
        if(Input.GetKeyDown(KeyCode.Insert))RequestTrainer();
        if(Time.realtimeSinceStartup<next)return; next=Time.realtimeSinceStartup+0.25f;
        var timer=System.Diagnostics.Stopwatch.StartNew();
        try {
            var command=incoming;
            Flags=command.Flags; Multiplier=command.Multiplier;
            if(DlcUnlocked!=command.Dlc){DlcUnlocked=command.Dlc;dlcPending=true;}
            if(dlcPending) {
                var gm=GameManager.GetInstance();
                if(gm!=null){dlcRefresh.Invoke(gm,null);dlcPending=false;}
            }
            if(command.Live || originalGod.Count>0 || freeOwned)ApplyLive();
            // All Unity/quest work stays on the main thread; all disk I/O is on IoLoop.
            if(command.Live && command.Quests && Time.realtimeSinceStartup>=nextQuests) {
                nextQuests=Time.realtimeSinceStartup+1f;
                try { UpdateQuests(true); } catch(Exception e) { error="Квесты: "+e.Message; }
            }
            var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene().name;
            string bits=String.Join("",Flags.Select(v=>v?"1":"0").ToArray());
            outgoingStatus=(ready?"ready":"error")+"\n"+ProcessId+"\n"+scene+"\n"+bits+"\n"+patched+"\n"+error.Replace('\n',' ').Replace('\r',' ')+"\nselftest="+(ready?"PASS":"FAIL")+"\nversion=1.4\nsession="+session+"\ndlc="+(DlcUnlocked?"1":"0");
        } catch(Exception e) {Flags=new bool[10];error=e.Message;}
        timer.Stop();tickCount++;totalTickMs+=timer.Elapsed.TotalMilliseconds;
        maxTickMs=Math.Max(maxTickMs,timer.Elapsed.TotalMilliseconds);
    }
    void RequestTrainer() {
        if(Time.realtimeSinceStartup<nextShow)return;
        nextShow=Time.realtimeSinceStartup+1f;
        AllowSetForegroundWindow(-1);
        System.Threading.Interlocked.Exchange(ref showRequest,1);
    }
    void OnGUI() {
        if(launcherStyle==null) {
            launcherStyle=new GUIStyle(GUI.skin.button);
            launcherStyle.fontSize=14;launcherStyle.fontStyle=FontStyle.Bold;
            launcherStyle.normal.textColor=new Color(1f,0.82f,0.86f);
        }
        if(GUI.Button(new Rect(Screen.width-188,16,172,34),"Трейнер  [Insert]",launcherStyle))RequestTrainer();
    }
    void IoLoop() {
        DateTime lastCommand=DateTime.MinValue, lastRequest=DateTime.MinValue, lastStatus=DateTime.MinValue;
        string statusWritten=null, questsWritten=null, resultWritten=null;
        while(ioRunning) {
            try {
                var now=DateTime.UtcNow;
                if(System.Threading.Interlocked.Exchange(ref showRequest,0)==1) {
                    AtomicText("show.txt",Guid.NewGuid().ToString("N"));
                    var heartbeat=Path.Combine(Root,"command.txt");
                    bool appLive=File.Exists(heartbeat) && (now-File.GetLastWriteTimeUtc(heartbeat)).TotalSeconds<5 && System.Diagnostics.Process.GetProcessesByName("CultTrainerRU").Length>0;
                    if(!appLive) {
                        string launcherFile=Path.Combine(Root,"launcher.txt");
                        if(File.Exists(launcherFile)) {
                            string launcher=File.ReadAllText(launcherFile).Trim();
                            if(Path.IsPathRooted(launcher) && Path.GetFileName(launcher).Equals("CultTrainerRU.exe",StringComparison.OrdinalIgnoreCase) && File.Exists(launcher))
                                try {System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(launcher){UseShellExecute=true});}
                                catch(Exception e){error="Не удалось открыть трейнер: "+e.Message;}
                        }
                    }
                }
                string path=Path.Combine(Root,"command.txt");
                DateTime stamp=File.Exists(path)?File.GetLastWriteTimeUtc(path):DateTime.MinValue;
                if(ready && (now-stamp).TotalSeconds<5) {
                    if(stamp!=lastCommand || !incoming.Live) {
                        var parts=File.ReadAllText(path).Trim().Split('|');
                        if(parts.Length==11 || parts.Length==12) {
                            int n; if(!int.TryParse(parts[10],out n))n=10;
                            incoming=new Command {Flags=parts.Take(10).Select(v=>v=="1").ToArray(),Multiplier=Math.Max(2,Math.Min(100,n)),Live=true,Quests=parts.Length==12 && parts[11]=="1"};
                            lastCommand=stamp;
                        }
                    }
                } else if(incoming.Live) incoming=new Command {Flags=new bool[10],Multiplier=10};
                if(incoming.Live) {
                    var viewPath=Path.Combine(Root,"quest-view.txt");
                    bool view=File.Exists(viewPath) && (now-File.GetLastWriteTimeUtc(viewPath)).TotalSeconds<2;
                    bool dlc=File.Exists(Path.Combine(Root,"dlc-unlock.txt"));
                    if(view!=incoming.Quests || dlc!=incoming.Dlc) {
                        var c=incoming;
                        incoming=new Command {Flags=c.Flags,Multiplier=c.Multiplier,Live=c.Live,Quests=view,Dlc=dlc};
                    }
                }
                if(incoming.Live && incoming.Quests) {
                    string request=Path.Combine(Root,"quest-command.txt");
                    var modified=File.Exists(request)?File.GetLastWriteTimeUtc(request):DateTime.MinValue;
                    if(modified>started && modified!=lastRequest && (now-modified).TotalSeconds<15) {
                        incomingQuest=File.ReadAllText(request).Trim();lastRequest=modified;
                    }
                }
                var status=outgoingStatus;
                if(status.Length>0 && status!=statusWritten) {AtomicText("status.txt",status);statusWritten=status;lastStatus=now;}
                else if(status.Length>0 && (now-lastStatus).TotalSeconds>=1) {File.SetLastWriteTimeUtc(Path.Combine(Root,"status.txt"),now);lastStatus=now;}
                var quests=outgoingQuests;
                if(quests!=null && quests!=questsWritten) {AtomicText("quests.txt",quests);questsWritten=quests;}
                var result=outgoingResult;
                if(result!=null && result!=resultWritten) {AtomicText("quest-result.txt",result);resultWritten=result;}
            } catch(IOException) {} catch(UnauthorizedAccessException) {}
              catch(Exception e) {error="IPC: "+e.Message;incoming=new Command {Flags=new bool[10],Multiplier=10};}
            System.Threading.Thread.Sleep(200);
        }
    }
    static void Background() { Application.runInBackground = true; }
    static string Encode(string text) { return Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes(text??"")); }
    static void AtomicText(string name,string text) {
        string temp=Path.Combine(Root,name+".tmp"),target=Path.Combine(Root,name);
        File.WriteAllText(temp,text);
        if(File.Exists(target))File.Replace(temp,target,null);else File.Move(temp,target);
    }
    void UpdateQuests(bool live) {
        var dm=DataManager.Instance;
        var active=dm==null || dm.Objectives==null?new List<ObjectivesData>():dm.Objectives.Where(q=>q!=null&&!q.IsComplete&&!q.IsFailed).ToList();
        var shown=active.Where(q=>ObjectiveManager.IsTracked(q.UniqueGroupID)).ToList();
        foreach(var q in shown)if(!questKeys.ContainsKey(q))questKeys[q]=Guid.NewGuid().ToString("N");
        string request=incomingQuest;
        if(live && request!=null) {
            var parts=request.Split('|');
            if(parts.Length==3 && parts[0]!=lastQuestRequest) {
                lastQuestRequest=parts[0];
                try {
                    if(parts[1]!=session)throw new Exception("Сеанс игры изменился. Обнови список заданий.");
                    var q=shown.FirstOrDefault(x=>questKeys[x]==parts[2]);
                    if(q==null)throw new Exception("Задание уже изменилось или больше не отслеживается.");
                    forcedQuests.Add(q);
                    try {if(!ObjectiveManager.UpdateObjective(q) || !q.IsComplete)throw new Exception("Игра не подтвердила завершение задания.");}
                    finally {forcedQuests.Remove(q);}
                    outgoingResult=(parts[0]+"|ok|"+Encode("Задание выполнено. Если требуется, забери награду у персонажа."));
                    Logger.LogInfo("Quest completed via game manager: "+q.GroupId+" / "+q.ID);
                } catch(Exception e) {outgoingResult=(parts[0]+"|error|"+Encode(e.Message));Logger.LogWarning(e);}
            }
        }
        var lines=new List<string>();lines.Add(session);
        foreach(var q in shown.Where(q=>!q.IsComplete&&!q.IsFailed)) {
            string text;try{text=q.Text;}catch{text="Задание";}
            string title=q.GroupId;
            try {
                if(!titleCache.TryGetValue(q.GroupId,out title)) {
                    title=translator==null?q.GroupId:(string)translator.Invoke(null,new object[]{q.GroupId,true,0,true,false,null,"Russian",false});
                    titleCache[q.GroupId]=title;
                }
            }catch{}
            lines.Add(questKeys[q]+"\t"+Encode(title)+"\t"+Encode(text));
        }
        var snapshot=String.Join("\n",lines.ToArray());
        if(snapshot!=lastQuestSnapshot){outgoingQuests=snapshot;lastQuestSnapshot=snapshot;}
        foreach(var q in questKeys.Keys.Where(q=>!active.Contains(q)).ToArray())questKeys.Remove(q);
    }
    static bool ForceQuest(ObjectivesData __instance,ref bool __result) {
        if(!forcedQuests.Contains(__instance))return true;
        __instance.Complete();__result=true;return false;
    }
    static bool DlcAccess(ref bool __result) {if(!DlcUnlocked)return true;__result=true;return false;}
    void ApplyLive() {
        if(PlayerFarming.players!=null)foreach(var p in PlayerFarming.players) {
            if(p==null || p.health==null)continue;
            var h=p.health;
            if(Flags[0]) {
                if(!originalGod.ContainsKey(h))originalGod[h]=h.GodMode;
                h.GodMode=(Health.CheatMode)3;
            } else if(originalGod.ContainsKey(h)) { h.GodMode=originalGod[h]; originalGod.Remove(h); }
        }
        if(Flags[6]) { if(!freeOwned){wasFree=CheatConsole.BuildingsFree;freeOwned=true;} CheatConsole.BuildingsFree=true; }
        else if(freeOwned) {CheatConsole.BuildingsFree=wasFree;freeOwned=false;}
        if(Flags[5] && CultFaithManager.Instance!=null && CultFaithManager.CurrentFaith!=85)CultFaithManager.CurrentFaith=85;
    }
    void OnDestroy() {ioRunning=false;DlcUnlocked=false;Logger.LogInfo("Main-thread tick avg/max ms: "+(tickCount==0?0:totalTickMs/tickCount)+" / "+maxTickMs);Flags=new bool[10];ApplyLive();if(harmony!=null)harmony.UnpatchSelf();}
    static bool Damage(ref bool __result) {if(!Flags[0])return true;__result=false;return false;}
    static bool Ammo(ref bool __result) {if(!Flags[7])return true;__result=true;return false;}
    static bool Afford(ref bool __result) {if(!Flags[7])return true;__result=true;return false;}
    static bool Dissent() {return !Flags[8];}
    static bool Sick() {return !Flags[9];}
    static bool Prayer(ref float __result) {if(!Flags[2])return true;__result=0.25f;return false;}
    static void Pickup(PickUp __instance,out int __state) {
        __state=__instance.Quantity;
        if(Flags[1] && __instance.AddToInventory && !Traverse.Create(__instance).Field("Collected").GetValue<bool>())
            __instance.Quantity=(int)Math.Min(1000000L,(long)__state*Multiplier);
    }
    static void PickupDone(PickUp __instance,int __state) {if(__instance!=null)__instance.Quantity=__state;}
    static void StatSet(MethodBase __originalMethod,ref float __0) {
        switch(__originalMethod.Name) {
            case "set_Satiation":if(Flags[3])__0=100;break;
            case "set_Starvation":if(Flags[3])__0=0;break;
            case "set_Rest":if(Flags[4])__0=100;break;
            case "set_Exhaustion":if(Flags[4])__0=0;break;
            case "set_Illness":if(Flags[9])__0=0;break;
            case "set_Dissent":if(Flags[8])__0=0;break;
            case "set_Faith":if(Flags[5])__0=100;break;
        }
    }
    static void FaithSet(ref float __0) {if(Flags[5])__0=85;}
}
