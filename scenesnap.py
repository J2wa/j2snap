"""SceneSnap: local scene timestamp to image exporter. Python 3.10+."""
import csv, html, json, os, queue, re, shutil, subprocess, sys, threading, time, uuid
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
TIME = r'\d+(?::\d{1,2}){1,2}(?:\.\d+)?'

def seconds(value):
    parts = [float(p) for p in value.split(':')]
    if any(p >= 60 for p in parts[1:]):
        raise ValueError('Invalid timestamp: ' + value)
    return sum(p * 60 ** i for i, p in enumerate(reversed(parts)))

def parse_scenes(text):
    headers = list(re.finditer(r'\bScene\s+(\d+)\b', text, re.I))
    if not headers:
        raise ValueError('No scenes found. Paste text containing Scene 1 and a start to end range.')
    rows, seen = [], {}
    for i, header in enumerate(headers):
        number = int(header[1])
        block = text[header.end():headers[i+1].start() if i+1 < len(headers) else len(text)]
        match = re.search(r'(' + TIME + r')\s*(?:to|–|—|-)\s*(' + TIME + r')', block, re.I)
        if not match:
            raise ValueError(f'Scene {number}: missing or malformed time range.')
        start, end = seconds(match[1]), seconds(match[2])
        if number < 1 or end <= start:
            raise ValueError(f'Scene {number}: end must be later than start.')
        row = (number, start, end)
        if number in seen:
            if seen[number] != row:
                raise ValueError(f'Scene {number} has conflicting ranges.')
            continue
        seen[number] = row
        rows.append(row)
    return sorted(rows)

def find_tool(name):
    suffix = '.exe' if os.name == 'nt' else ''
    for p in (BASE / 'bin' / (name + suffix), BASE / (name + suffix)):
        if p.is_file(): return str(p)
    return shutil.which(name) or ''

def run(args, stop=None, timeout=60):
    if stop and stop.is_set(): raise InterruptedError("Cancelled. Completed images are retained.")
    deadline = time.monotonic() + timeout
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=flags)
    try:
        while True:
            try:
                out, err = p.communicate(timeout=0.2)
                break
            except subprocess.TimeoutExpired:
                if time.monotonic() >= deadline:
                    p.kill(); p.communicate()
                    raise TimeoutError(f'Video operation exceeded {timeout} seconds. Try a local copy of the video or a shorter file.')
                if stop and stop.is_set():
                    p.kill(); p.communicate()
                    raise InterruptedError('Cancelled. Completed images are retained.')
        if p.returncode: raise RuntimeError(err[-1800:] or 'Video tool failed.')
        return out
    finally:
        if p.poll() is None: p.kill(); p.wait()

def export(video, rows, output, ffmpeg, ffprobe, stop, progress):
    info = json.loads(run([ffprobe, '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(video)], stop))
    if not any(s.get('codec_type') == 'video' for s in info.get('streams', [])):
        raise ValueError('The selected file has no video stream.')
    duration = float(info['format']['duration'])
    if max(r[2] for r in rows) > duration + 0.15:
        raise ValueError(f'Scenes end at {max(r[2] for r in rows):.1f}s but video lasts {duration:.1f}s. Select the matching original video.')
    folder = Path(output) / ('SceneSnap_' + datetime.now().strftime('%Y%m%d_%H%M%S_') + uuid.uuid4().hex[:6])
    folder.mkdir(parents=True)
    progress(0, len(rows), str(folder))
    cards = []
    done = 0
    with (folder / 'snapshots.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['scene','start_seconds','end_seconds','requested_start_seconds','image'])
        try:
            for scene, start, end in rows:
                images = []
                if stop.is_set(): raise InterruptedError('Cancelled. Completed images are retained.')
                name = f'videoframe_{scene}_1.png'
                path = folder / name
                # Input seeking decodes only from the preceding keyframe; no full-video scan.
                # Restrict output to this scene and return its first frame at/after start.
                try:
                    run([ffmpeg, '-nostdin', '-v', 'error', '-ss', f'{start:.6f}',
                         '-i', str(video), '-t', f'{end-start:.6f}', '-map', '0:v:0',
                         '-frames:v', '1', '-update', '1', str(path)], stop)
                except (TimeoutError, RuntimeError) as exc:
                    raise RuntimeError(f'Scene {scene} at {start:.3f}s: {exc}') from exc
                if not path.exists() or path.stat().st_size == 0:
                    raise RuntimeError(f'No frame available inside scene {scene} at {start:.3f}s.')
                writer.writerow([scene,start,end,start,name]); f.flush()
                images.append(f'<a href="{name}"><img loading="lazy" src="{name}"><span>Start {start:.3f}s</span></a>')
                done += 1
                progress(done, len(rows), str(folder))
                cards.append(f'<section><h2>Scene {scene} <small>{start:.1f}–{end:.1f}s</small></h2><div>{"".join(images)}</div></section>')
        finally:
            (folder/'gallery.html').write_text('<!doctype html><meta charset="utf-8"><title>SceneSnap gallery</title><style>body{background:#0d1729;color:#e7eefb;font:16px system-ui;margin:32px}h1{color:#8fbaff}small{font-size:14px;color:#9eb0ca}section{margin:28px 0}div{display:flex;flex-wrap:wrap;gap:12px}a{width:300px;color:#b8d4ff;text-decoration:none}img{width:100%;display:block;border-radius:8px}span{display:block;padding:8px}</style><h1>SceneSnap gallery</h1><p>First frame at or after each scene start. Labels show requested start times. Partial exports show completed scenes.</p>'+''.join(cards), encoding='utf-8')
    return folder

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('SceneSnap — Video snapshots'); self.geometry('940x790'); self.minsize(780,650)
        self.events=queue.Queue(); self.stop=threading.Event(); self.busy=False; self.folder=None
        style=ttk.Style(self); style.theme_use('clam')
        style.configure('TFrame',background='#edf3fb'); style.configure('TLabel',background='#edf3fb',foreground='#15243b')
        style.configure('TButton',padding=7); style.configure('Title.TLabel',font=('Segoe UI',22,'bold'))
        box=ttk.Frame(self,padding=22); box.pack(fill='both',expand=True); box.columnconfigure(1,weight=1)
        ttk.Label(box,text='SceneSnap',style='Title.TLabel').grid(row=0,column=0,columnspan=3,sticky='w')
        ttk.Label(box,text='Paste scene ranges. Choose your video. Export images locally.').grid(row=1,column=0,columnspan=3,sticky='w',pady=(0,15))
        self.video=tk.StringVar(); self.output=tk.StringVar(value=str(Path.home()/'Pictures')); self.ffmpeg=tk.StringVar(value=find_tool('ffmpeg')); self.ffprobe=tk.StringVar(value=find_tool('ffprobe'))
        for row,label,var,kind in [(2,'Video file',self.video,'file'),(3,'Save folder',self.output,'dir'),(4,'ffmpeg.exe',self.ffmpeg,'file'),(5,'ffprobe.exe',self.ffprobe,'file')]:
            if row in (4,5) and getattr(sys, 'frozen', False): continue
            ttk.Label(box,text=label).grid(row=row,column=0,sticky='w',padx=(0,12))
            ttk.Entry(box,textvariable=var).grid(row=row,column=1,sticky='ew',pady=4)
            ttk.Button(box,text='Browse',command=lambda v=var,k=kind:self.browse(v,k)).grid(row=row,column=2,padx=(8,0))
        bar=ttk.Frame(box); bar.grid(row=6,column=0,columnspan=3,sticky='ew',pady=10)
        ttk.Label(bar,text='Scene text').pack(side='left')
        ttk.Button(bar,text='Import .txt',command=self.import_text).pack(side='right')
        ttk.Button(bar,text='Paste clipboard',command=self.paste).pack(side='right',padx=8)
        self.text=tk.Text(box,height=12,wrap='word',font=('Consolas',10),undo=True)
        self.text.grid(row=7,column=0,columnspan=3,sticky='nsew'); box.rowconfigure(7,weight=1)
        sample=BASE/'example-scenes.txt'
        if sample.exists(): self.text.insert('1.0',sample.read_text(encoding='utf-8-sig'))
        options=ttk.Frame(box); options.grid(row=8,column=0,columnspan=3,sticky='ew',pady=12)
        ttk.Label(options,text='One image per scene · First frame').pack(side='left')
        ttk.Button(options,text='Validate scenes',command=self.validate).pack(side='right')
        self.status=tk.StringVar(value='Ready. Paste or import your scene list.')
        ttk.Label(box,textvariable=self.status,wraplength=850).grid(row=9,column=0,columnspan=3,sticky='w')
        self.progress=ttk.Progressbar(box,maximum=100); self.progress.grid(row=10,column=0,columnspan=3,sticky='ew',pady=12)
        actions=ttk.Frame(box); actions.grid(row=11,column=0,columnspan=3,sticky='ew')
        self.start=ttk.Button(actions,text='Generate snapshots',command=self.generate); self.start.pack(side='left')
        self.cancel=ttk.Button(actions,text='Cancel',command=self.stop.set,state='disabled'); self.cancel.pack(side='left',padx=8)
        ttk.Button(actions,text='Open results',command=self.open_results).pack(side='right')
        self.protocol('WM_DELETE_WINDOW',self.close); self.after(100,self.poll)
    def browse(self,var,kind):
        p=filedialog.askdirectory() if kind=='dir' else filedialog.askopenfilename()
        if p: var.set(p)
    def import_text(self):
        p=filedialog.askopenfilename(filetypes=[('Text files','*.txt'),('All files','*.*')])
        if p:
            try:
                value=Path(p).read_text(encoding='utf-8-sig'); self.text.delete('1.0','end'); self.text.insert('1.0',value)
            except Exception as e: messagebox.showerror('Import failed',str(e))
    def paste(self):
        try:
            value=self.clipboard_get(); self.text.delete('1.0','end'); self.text.insert('1.0',value)
        except tk.TclError: messagebox.showerror('Clipboard','Copy the scene text first.')
    def validate(self):
        try:
            rows=parse_scenes(self.text.get('1.0','end'))
            gaps=sum(b[0]!=a[0]+1 for a,b in zip(rows,rows[1:]))
            self.status.set(f'{len(rows)} scenes · last endpoint {rows[-1][2]:.1f}s · {gaps} scene-number gaps. Time gaps are preserved.')
            return rows
        except Exception as e: messagebox.showerror('Check scene text',str(e))
    def generate(self):
        if self.busy: return
        rows=self.validate()
        if not rows: return
        try:
            for label,p in [('Video',self.video.get()),('FFmpeg',self.ffmpeg.get()),('FFprobe',self.ffprobe.get())]:
                if not Path(p).is_file(): raise ValueError(f'{label}: choose an existing file. See README for setup.')
            if not Path(self.output.get()).is_dir(): raise ValueError('Choose an existing save folder.')
        except Exception as e: messagebox.showerror('Setup required',str(e)); return
        args=(self.video.get(),rows,self.output.get(),self.ffmpeg.get(),self.ffprobe.get())
        self.stop.clear(); self.busy=True; self.folder=None; self.progress['value']=0
        self.start['state']='disabled'; self.cancel['state']='normal'; self.status.set('Checking video metadata… (up to 60 seconds)')
        def worker():
            try:
                folder=export(*args,self.stop,lambda n,total,path:self.events.put(('progress',n,total,path)))
                self.events.put(('done',str(folder)))
            except Exception as e: self.events.put(('error',str(e)))
        threading.Thread(target=worker,daemon=True).start()
    def poll(self):
        try:
            while True:
                event=self.events.get_nowait()
                if event[0]=='progress':
                    _,n,total,self.folder=event; self.progress['value']=100*n/total; self.status.set(f'{n} / {total} images saved' + (' · Capturing next scene…' if n < total else ' · Finishing…'))
                else:
                    self.busy=False; self.start['state']='normal'; self.cancel['state']='disabled'
                    if event[0]=='done': self.folder=event[1]; self.status.set('Finished. Open results for PNG images, gallery and CSV.')
                    else:
                        self.status.set(event[1]); messagebox.showinfo('Export stopped',event[1])
        except queue.Empty: pass
        self.after(100,self.poll)
    def open_results(self):
        if not self.folder: return messagebox.showinfo('Results','Generate snapshots first.')
        import webbrowser
        webbrowser.open((Path(self.folder)/'gallery.html').as_uri())
    def close(self):
        if self.busy:
            self.stop.set(); messagebox.showinfo('Stopping','Cancellation requested. Close again after export stops.'); return
        self.destroy()

def self_test(destination):
    import tempfile
    try:
        assert len(parse_scenes('Scene 1\n0:00.0 to 0:01.0\nScene 2\n0:01.0 to 0:03.0')) == 2
        with tempfile.TemporaryDirectory() as d:
            video = Path(d)/'test.mp4'
            run([find_tool('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=25:duration=3', '-c:v', 'mpeg4', str(video)])
            rows = [(1,0,1),(2,1.01,2),(3,2.96,3)]
            updates = []
            folder = export(video, rows, d, find_tool('ffmpeg'), find_tool('ffprobe'), threading.Event(), lambda *args: updates.append(args))
            assert len(list(folder.glob('*.png'))) == 3
            assert [u[0] for u in updates] == [0,1,2,3]
            records = list(csv.DictReader((folder/'snapshots.csv').open()))
            assert [r['image'] for r in records] == ['videoframe_1_1.png','videoframe_2_1.png','videoframe_3_1.png']
            for record, index in zip(records, [0,26,74]):
                reference = Path(d)/'reference.png'
                run([find_tool('ffmpeg'), '-y', '-v', 'error', '-i', str(video), '-vf', f'select=eq(n\\,{index})', '-frames:v', '1', '-update', '1', str(reference)])
                assert reference.read_bytes() == (folder/record['image']).read_bytes()
            cancelled = threading.Event(); cancelled.set()
            try: run([find_tool('ffprobe'), '-version'], cancelled)
            except InterruptedError: pass
            else: raise AssertionError('Cancellation ignored')
            try:
                run([find_tool('ffmpeg'), '-v', 'error', '-re', '-f', 'lavfi', '-i', 'color=size=16x16:rate=1', '-t', '10', '-f', 'null', '-'], timeout=0.1)
            except TimeoutError: pass
            else: raise AssertionError('Timeout ignored')
            app = App(); app.update(); app.destroy()
        Path(destination).write_text('PASS: one first-frame PNG per scene; non-aligned start and EOF pixels; filenames; progress; cancellation; timeout; packaged tools and native window.', encoding='utf-8')
    except Exception:
        import traceback
        Path(destination).write_text(traceback.format_exc(), encoding='utf-8')
        raise

if __name__=='__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test': self_test(sys.argv[2])
    else: App().mainloop()

