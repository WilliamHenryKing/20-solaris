"""Run one local CUDA render while preserving the measured machine reserves."""
import argparse
import ctypes
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent
BLENDER = ROOT / '.workspace/blender-runtime/Blender Foundation/Blender 5.2/blender.exe'

def suspend_renderer(pid, suspended):
    """Pause only our own Blender child; preserve the current sample accumulation.
    No system power/fan/driver setting is changed, and unrelated processes are untouched.
    """
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.restype=ctypes.c_void_p
    handle=kernel.OpenProcess(0x0800,False,pid)
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    ntdll=ctypes.WinDLL('ntdll')
    operation=ntdll.NtSuspendProcess if suspended else ntdll.NtResumeProcess
    operation.argtypes=[ctypes.c_void_p]
    operation.restype=ctypes.c_long
    try:
        status=operation(handle)
        if status<0:raise OSError(f'Render process pause/resume failed: {status}')
    finally:
        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        kernel.CloseHandle(handle)

class MemoryStatus(ctypes.Structure):
    _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong), ('total', ctypes.c_ulonglong), ('available', ctypes.c_ulonglong), ('total_page', ctypes.c_ulonglong), ('available_page', ctypes.c_ulonglong), ('total_virtual', ctypes.c_ulonglong), ('available_virtual', ctypes.c_ulonglong), ('available_extended', ctypes.c_ulonglong)]

class ProcessMemory(ctypes.Structure):
    _fields_=[('cb',ctypes.c_ulong),('faults',ctypes.c_ulong)]+[(key,ctypes.c_size_t) for key in ('peakWorking','working','peakPaged','paged','peakNonPaged','nonPaged','pagefile','peakPagefile','private')]

def sample(start,process=None):
    raw = subprocess.check_output(['nvidia-smi', '--query-gpu=temperature.gpu,memory.free,memory.used,utilization.gpu', '--format=csv,noheader,nounits'], text=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=5)
    temp, free, used, utilization = [int(n.strip()) for n in raw.splitlines()[0].split(',')]
    ram = MemoryStatus()
    ram.length = ctypes.sizeof(ram)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ram))
    state={'elapsedSeconds': round(time.time()-start, 2), 'gpuC': temp, 'freeVramMiB': free, 'usedVramMiB': used, 'gpuPercent': utilization, 'freeRamMiB': round(ram.available / 1024**2),'freeCommitMiB':round(ram.available_page/1024**2)}
    if process:
        counters=ProcessMemory();counters.cb=ctypes.sizeof(counters)
        query=ctypes.WinDLL('psapi').GetProcessMemoryInfo
        query.argtypes=[ctypes.c_void_p,ctypes.POINTER(ProcessMemory),ctypes.c_ulong]
        query.restype=ctypes.c_int
        if query(int(process._handle),ctypes.byref(counters),ctypes.sizeof(counters)):
            state.update({'rendererWorkingMiB':round(counters.working/1024**2),'rendererPrivateMiB':round(counters.private/1024**2)})
    return state

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--scene', required=True, choices=['aurel', 'strata', 'solaris'])
    p.add_argument('--quality', default='final', choices=['draft', 'final'])
    p.add_argument('--output', required=True)
    p.add_argument('--samples', type=int)
    p.add_argument('--world', action='store_true')
    p.add_argument('--validate', action='store_true')
    p.add_argument('--blend')
    p.add_argument('--metadata')
    p.add_argument('--region', type=int, nargs=4)
    p.add_argument('--view', choices=['wide','detail'], default='wide')
    args = p.parse_args()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
    evidence = {'scene': args.scene, 'view':args.view, 'quality': args.quality, 'guards': {'maxGpuC':85, 'pauseGpuC':79, 'resumeGpuC':59, 'minFreeVramMiB':1024, 'minFreeRamMiB':1536, 'pauseFreeRamMiB':2048, 'resumeFreeRamMiB':2304}, 'samples': [sample(start)], 'coolingPeriods':[]}
    def breach(state):
        return state['gpuC'] >= 85 or state['freeVramMiB'] < 1024 or state['freeRamMiB'] < 1536
    if breach(evidence['samples'][0]):
        raise RuntimeError('Render not started: machine reserve guard is already exceeded.')
    if bool(args.blend)!=bool(args.region):p.error('--blend and --region must be supplied together')
    if args.metadata and not args.blend:p.error('--metadata is only valid with --blend')
    if args.validate and args.blend:p.error('--validate cannot be combined with a cropped render')
    evidence['operation']='scene-preparation' if args.validate else ('region-render' if args.blend else 'full-render')
    evidence['guards']['maxMemoryPauseSeconds']=600
    script = 'render-architecture-region.py' if args.blend else ('render-architecture-world.py' if args.world else 'render-architecture-cuda.py')
    command = [str(BLENDER), '--background', '--factory-startup', '--python-exit-code', '1', '--python', str(ROOT/'tools'/script), '--', '--scene', args.scene, '--quality', args.quality, '--output', str(output)]
    if args.world or args.blend: command += ['--view', args.view]
    if args.validate:command += ['--validate']
    if args.blend:command += ['--blend',str(Path(args.blend).resolve()),'--region',*[str(n) for n in args.region]]
    if args.metadata:command += ['--metadata',str(Path(args.metadata).resolve())]
    if args.samples:
        command += ['--samples', str(args.samples)]
    with output.with_suffix('.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT, creationflags=subprocess.CREATE_NO_WINDOW)
        stopped = False
        paused = False
        pause_start = None
        memory_pause = False
        low_memory_samples = 0
        recovery_start = None
        last_report = start
        last_progress = 0
        try:
            while process.poll() is None:
                state = sample(start,process)
                evidence['samples'].append(state)
                if time.time()-last_progress >= 15:
                    output.with_suffix('.progress.json').write_text(json.dumps({'checkedAt':time.time(),'pid':process.pid,'paused':paused,'memoryPressure':memory_pause,'state':state}),encoding='utf-8')
                    last_progress=time.time()
                if breach(state):
                    stopped = True
                    evidence['stopReason']='Hard machine reserve threshold exceeded'
                    process.terminate()
                    process.wait(timeout=20)
                    break
                low_memory_samples = low_memory_samples+1 if state['freeRamMiB'] < 2048 else 0
                if not paused and (state['gpuC'] >= 79 or low_memory_samples >= 2):
                    suspend_renderer(process.pid,True)
                    paused=True
                    pause_start=time.time()
                    memory_pause=low_memory_samples >= 2
                    recovery_start=None
                    print(f"Resource pause at {state['gpuC']}C / {state['freeRamMiB']}MiB RAM free; render samples preserved.",flush=True)
                elif paused:
                    memory_pause=memory_pause or low_memory_samples >= 2
                    recovered=state['freeRamMiB'] >= 2304 if memory_pause else state['freeRamMiB'] >= 2048
                    recovery_start=(recovery_start or time.time()) if recovered else None
                    ready=state['gpuC'] <= 59 and recovered and (not memory_pause or time.time()-recovery_start >= 10)
                    if memory_pause and time.time()-pause_start > 600:
                        stopped=True
                        evidence['stopReason']='Memory did not recover within the bounded pressure pause'
                        process.terminate();process.wait(timeout=20)
                        break
                    if not ready:
                        time.sleep(1.5)
                        continue
                    suspend_renderer(process.pid,False)
                    paused=False
                    evidence['coolingPeriods'].append({'startedAtSecond':round(pause_start-start,2),'durationSeconds':round(time.time()-pause_start,2),'resumedGpuC':state['gpuC'],'memoryPressure':memory_pause})
                    print(f"Resuming CUDA at {state['gpuC']}C / {state['freeRamMiB']}MiB RAM free.",flush=True)
                if time.time()-last_report >= 60:
                    print(f"Render active {state['elapsedSeconds']}s; {state['gpuC']}C; RAM free {state['freeRamMiB']}MiB; VRAM free {state['freeVramMiB']}MiB.",flush=True)
                    last_report=time.time()
                time.sleep(1.5)
        except BaseException as error:
            stopped=True
            evidence['monitorError']=str(error)
        finally:
            if process.poll() is None:
                # On interruption or a failed monitor, never leave our child
                # suspended indefinitely or running without reserve checks.
                process.terminate()
                try: process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait(timeout=10)
            if paused:
                evidence['coolingPeriods'].append({'startedAtSecond':round(pause_start-start,2),'durationSeconds':round(time.time()-pause_start,2),'interrupted':True})
    evidence.update({'exitCode':process.returncode, 'guardStopped':stopped, 'elapsedSeconds':round(time.time()-start,2), 'maxGpuC':max(x['gpuC'] for x in evidence['samples']), 'minFreeVramMiB':min(x['freeVramMiB'] for x in evidence['samples']), 'minFreeRamMiB':min(x['freeRamMiB'] for x in evidence['samples'])})
    output.with_suffix('.machine.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in evidence.items() if k != 'samples'}))
    expected_output=output.with_suffix('.blend') if args.validate else output
    if stopped or process.returncode or not expected_output.exists() or expected_output.stat().st_mtime < start:
        print(output.with_suffix('.log').read_text(encoding='utf-8')[-3000:])
        raise SystemExit(1)
    print('Saved '+str(output))

if __name__ == '__main__':
    main()
