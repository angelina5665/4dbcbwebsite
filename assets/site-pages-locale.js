(function () {
  'use strict';
  if (!window.SiteLocale || window.SitePagesLocale) return;

  const api = window.SiteLocale;
  const originalTitle = document.title;
  const originalText = new WeakMap();
  const originalHtml = new WeakMap();
  const common = {
    ms: {
      'Home':'Utama','Results':'Keputusan','Result':'Keputusan','Prize history':'Sejarah hadiah','Past results':'Keputusan lepas','Dictionary':'Kamus nombor','Guide':'Panduan','About':'Tentang kami','Sources & Method':'Sumber & Kaedah','Methodology & Sources':'Metodologi & Sumber','Privacy':'Privasi','Privacy Notice':'Notis Privasi','Disclaimer':'Penafian','Affiliate Disclosure':'Pendedahan Afiliasi','Sitemap':'Peta laman','Language':'Bahasa','Theme':'Tema','System':'Sistem','Light':'Cerah','Dark':'Gelap',
      'Latest completed result':'Keputusan lengkap terkini','Provider comparison':'Perbandingan penyedia','Most recent provider draw shown:':'Cabutan penyedia terkini dipaparkan:','Data file updated:':'Fail data dikemas kini:','Retained data imported:':'Data tersimpan diimport:','Use this as a reference and verify important results with the relevant provider.':'Gunakan sebagai rujukan dan sahkan keputusan penting dengan penyedia berkaitan.','Draw date:':'Tarikh cabutan:','Draw':'Cabutan','1st prize':'Hadiah pertama','2nd prize':'Hadiah kedua','3rd prize':'Hadiah ketiga','Special':'Hadiah khas','Starter':'Hadiah permulaan','Consolation':'Hadiah saguhati','Top prizes for':'Hadiah utama untuk',
      'Payout Table':'Jadual Bayaran','How To Bet':'Cara Bertaruh','Straight and IBOX reference':'Rujukan Straight dan IBOX','Five steps and a practice slip':'Lima langkah dan slip latihan','INDEPENDENT 4D REFERENCE':'RUJUKAN 4D BEBAS','4D Payout & Play Guide':'Panduan Bayaran & Permainan 4D','PAYOUT TABLE':'JADUAL BAYARAN','Standard straight 4D prize reference':'Rujukan hadiah 4D straight standard','Sources checked 3 Oct 2026':'Sumber disemak 3 Okt 2026','Prize category':'Kategori hadiah','Big / ABC':'Big / ABC','Small / A':'Small / A','1st Prize':'Hadiah Pertama','2nd Prize':'Hadiah Kedua','3rd Prize':'Hadiah Ketiga','Special / Starter':'Khas / Permulaan','View IBOX / permutation payout table':'Lihat jadual bayaran IBOX / permutasi','Official sources':'Sumber rasmi','HOW TO BET':'CARA BERTARUH','Understand a basic 4D entry in five steps':'Fahami penyertaan asas 4D dalam lima langkah','Choose a provider':'Pilih penyedia','Enter four digits':'Masukkan empat digit','Choose straight or permutation':'Pilih straight atau permutasi','Choose Big or Small':'Pilih Big atau Small','Review before confirming':'Semak sebelum mengesahkan','PRACTICE ONLY':'LATIHAN SAHAJA','Build an example slip':'Bina contoh slip','No bet is placed':'Tiada pertaruhan dibuat','Provider':'Penyedia','Four-digit number':'Nombor empat digit','Play type':'Jenis permainan','Pool':'Pilihan','Example amount (RM)':'Jumlah contoh (RM)','Preview example':'Pratonton contoh','Important':'Penting','Payout & How to Bet Guide':'Panduan Bayaran & Cara Bertaruh','Independent information website.':'Laman maklumat bebas.'
    },
    zh: {
      'Home':'首页','Results':'开彩结果','Result':'开彩结果','Prize history':'历史奖号','Past results':'历史结果','Dictionary':'号码辞典','Guide':'指南','About':'关于我们','Sources & Method':'来源与方法','Methodology & Sources':'方法与来源','Privacy':'隐私','Privacy Notice':'隐私声明','Disclaimer':'免责声明','Affiliate Disclosure':'推广披露','Sitemap':'网站地图','Language':'语言','Theme':'主题','System':'跟随系统','Light':'浅色','Dark':'深色',
      'Latest completed result':'最新完整结果','Provider comparison':'运营商比较','Most recent provider draw shown:':'显示的最新运营商开彩：','Data file updated:':'数据文件更新时间：','Retained data imported:':'保留数据导入时间：','Use this as a reference and verify important results with the relevant provider.':'本页仅供参考；重要结果请向相关运营商核实。','Draw date:':'开彩日期：','Draw':'期号','1st prize':'头奖','2nd prize':'二奖','3rd prize':'三奖','Special':'特别奖','Starter':'入围奖','Consolation':'安慰奖','Top prizes for':'主要奖项：',
      'Payout Table':'奖金表','How To Bet':'如何下注','Straight and IBOX reference':'Straight 与 IBOX 参考','Five steps and a practice slip':'五个步骤与模拟注单','INDEPENDENT 4D REFERENCE':'独立 4D 参考资料','4D Payout & Play Guide':'4D 奖金与玩法指南','PAYOUT TABLE':'奖金表','Standard straight 4D prize reference':'标准 Straight 4D 奖金参考','Sources checked 3 Oct 2026':'来源核对于 2026年10月3日','Prize category':'奖项类别','Big / ABC':'大 / ABC','Small / A':'小 / A','1st Prize':'头奖','2nd Prize':'二奖','3rd Prize':'三奖','Special / Starter':'特别奖 / 入围奖','View IBOX / permutation payout table':'查看 IBOX / 排列奖金表','Official sources':'官方来源','HOW TO BET':'如何下注','Understand a basic 4D entry in five steps':'五个步骤了解基本 4D 注单','Choose a provider':'选择运营商','Enter four digits':'输入四位数字','Choose straight or permutation':'选择 Straight 或排列玩法','Choose Big or Small':'选择大或小','Review before confirming':'确认前检查','PRACTICE ONLY':'仅供练习','Build an example slip':'建立模拟注单','No bet is placed':'不会进行真实下注','Provider':'运营商','Four-digit number':'四位号码','Play type':'玩法','Pool':'投注类别','Example amount (RM)':'示例金额（RM）','Preview example':'预览示例','Important':'重要提示','Payout & How to Bet Guide':'奖金与下注指南','Independent information website.':'独立资讯网站。'
    }
  };

  const legal = {
    '/about.html': {
      ms: `<h1>Tentang 4DVIP88</h1><p class="effective"><strong>Halaman dikemas kini:</strong> 24 Ogos 2026</p><p>4DVIP88 ialah laman rujukan bebas yang menggabungkan maklumat cabutan 4D terkini daripada beberapa penyedia. Laman ini tidak menerima pertaruhan, menyimpan wang pelawat, membuka akaun pertaruhan atau memproses deposit dan pengeluaran.</p><h2>Apa yang dipaparkan</h2><p>Halaman utama memuatkan fail data daripada laman yang sama dan memaparkan maklumat terkini dalam fail itu. Masa kemas kini menunjukkan kesegaran suapan, bukan bukti bahawa setiap nombor lengkap, tepat atau muktamad.</p><h2>Status bebas</h2><p>4DVIP88 tidak dikendalikan, diberi kuasa atau disokong oleh penyedia keputusan yang dinamakan. Nama dan logo penyedia digunakan untuk mengenal pasti maklumat. Sahkan keputusan penting terus dengan penyedia berkaitan.</p><h2>Batas editorial</h2><ul><li>Tiada ramalan atau dakwaan kemenangan dan bayaran terjamin.</li><li>Tiada dakwaan bahawa laman ini atau pengiklan ialah penyedia rasmi.</li><li>Halaman penyedia atau arkib tidak diterbitkan tanpa semakan sumber data, asas penggunaan semula dan nilai pengguna.</li><li>Versi bahasa hanya dipaparkan apabila kandungannya benar-benar diterjemah dan disemak.</li></ul><h2>Pengiklanan</h2><p>Laman ini mengandungi pautan tajaan yang mungkin memberi pampasan apabila pelawat mengikuti pautan atau melengkapkan tindakan di destinasi. Iklan dilabel dan dipisahkan daripada pengesahan keputusan.</p><p class="note">Untuk maklumat tentang pengendalian data, had sumber dan iklan, baca Notis Privasi, Metodologi &amp; Sumber, Penafian dan Pendedahan Afiliasi.</p>`,
      zh: `<h1>关于 4DVIP88</h1><p class="effective"><strong>页面更新：</strong>2026年8月24日</p><p>4DVIP88 是一个独立参考网站，将多个运营商近期的 4D 开彩资料集中显示。本站不接受投注、不保管访客资金、不创建投注账户，也不处理存款或提款。</p><h2>网站显示什么</h2><p>首页读取同一网站的数据文件，并显示该文件中最新的资料。更新时间只反映数据源的新鲜度，并不证明所有号码完整、准确或最终有效。</p><h2>独立性质</h2><p>4DVIP88 并非由所列运营商经营、授权或认可。运营商名称和标志仅用于识别资料。重要结果请直接向相关运营商核实。</p><h2>编辑原则</h2><ul><li>不作预测，也不声称保证中奖或保证付款。</li><li>不声称本站或广告商是官方运营商。</li><li>未审查数据来源、转载依据和用户价值前，不发布运营商或存档页面。</li><li>只有内容经过真实翻译和审阅后，才会标示为完整语言版本。</li></ul><h2>广告</h2><p>网站含有赞助链接；访客点击或在目标网站完成操作时，本站可能获得报酬。广告会明确标示，并与开奖结果核实分开。</p><p class="note">有关数据处理、来源限制和广告的详情，请阅读隐私声明、方法与来源、免责声明和推广披露。</p>`
    },
    '/disclaimer.html': {
      ms: `<h1>Penafian</h1><p class="effective"><strong>Tarikh berkuat kuasa:</strong> 23 Ogos 2026</p><h2>Maklumat untuk rujukan</h2><p>Maklumat keputusan di my4d.co disediakan untuk rujukan umum. Ia mungkin lewat, tidak lengkap atau salah akibat perubahan sumber, kegagalan penghantaran, ralat pemprosesan atau pembetulan kemudian. Sahkan keputusan terus dengan penyedia sebelum bergantung padanya.</p><h2>Laman bebas</h2><p>Laman maklumat ini bebas dan tidak dikendalikan, diberi kuasa atau disokong oleh penyedia yang dinamakan. Nama dan logo kekal milik pihak masing-masing.</p><h2>Tiada pertaruhan atau jaminan hasil</h2><p>Laman ini tidak menerima pertaruhan, menyimpan wang, memproses deposit atau pengeluaran, atau memberi nasihat pertaruhan peribadi. Ia tidak meramal nombor menang dan tidak menjamin kemenangan, hadiah, bayaran, kelulusan akaun atau hasil lain.</p><p class="important">Patuhi undang-undang dan had umur di lokasi anda. Jika maklumat mempengaruhi keputusan, semak dengan penyedia dahulu.</p><h2>Pautan tajaan</h2><p>Sesetengah sepanduk dan pautan ditaja dan mungkin memberi pampasan kepada laman ini. Iklan tidak menjadikan perkhidmatan tersebut sumber keputusan rasmi dan bukan dakwaan tentang lesen, keselamatan, kebolehpercayaan, bonus atau bayaran.</p><p>Laman luar menetapkan terma, kelayakan dan amalan privasi sendiri. Nilai destinasi secara bebas sebelum memberi maklumat peribadi atau bayaran.</p><h2>Ketersediaan dan perubahan</h2><p>Halaman, suapan keputusan dan pautan luar boleh berubah atau tidak tersedia tanpa notis. Pembetulan penting akan disertakan dengan tarikh berkuat kuasa yang dikemas kini.</p>`,
      zh: `<h1>免责声明</h1><p class="effective"><strong>生效日期：</strong>2026年8月23日</p><h2>仅供参考</h2><p>my4d.co 的结果资料仅供一般参考。由于来源变更、传输失败、处理错误或后续修正，资料可能延迟、不完整或不准确。依赖任何结果前，请直接向相关运营商核实。</p><h2>独立网站</h2><p>本站是独立资讯网站，并非由所列运营商经营、授权或认可。运营商名称和标志只用于识别资料，权利归各自所有者。</p><h2>不接受投注，也不保证结果</h2><p>本站不接受投注、不保管资金、不处理存提款，也不提供个人投注建议。本站不预测中奖号码，也不保证中奖、奖金、付款、账户批准或任何其他结果。</p><p class="important">请遵守所在地法律和年龄限制。若结果资料会影响决定，请先向相关运营商核实。</p><h2>赞助链接</h2><p>部分横幅和链接为赞助内容，本站可能因此获得报酬。广告不会使相关服务成为官方结果来源，也不代表对其牌照、安全、可靠性、优惠或付款作出保证。</p><p>外部网站自行制定条款、资格规定和隐私政策。提供个人或付款资料前，请自行评估目标网站。</p><h2>可用性与更改</h2><p>页面、结果数据源和外部链接可能随时更改或无法使用。重大修正会更新上方生效日期。</p>`
    },
    '/affiliate-disclosure.html': {
      ms: `<h1>Pendedahan Afiliasi</h1><p class="effective"><strong>Tarikh berkuat kuasa:</strong> 24 Ogos 2026</p><p>Sesetengah sepanduk dan pautan di 4DVIP88 ialah pautan tajaan atau afiliasi. Laman ini mungkin menerima pampasan apabila pelawat mengikutinya atau melengkapkan tindakan di laman destinasi.</p><h2>Cara pautan tajaan dikenal pasti</h2><p>Iklan halaman utama mempunyai label “Ditaja”, dan pautan tajaan menggunakan atribut <code>rel="sponsored"</code>. Ini membezakan iklan daripada maklumat keputusan.</p><h2>Maksud yang tidak terkandung dalam pampasan</h2><ul><li>Ia tidak menjadikan pengiklan sumber keputusan rasmi.</li><li>Ia bukan dakwaan bahawa pengiklan berlesen, selamat, boleh dipercayai atau sesuai untuk semua pelawat.</li><li>Ia bukan janji kelulusan pendaftaran, bonus, bayaran atau kemenangan.</li><li>Ia tidak mengesahkan secara bebas keputusan di 4DVIP88.</li></ul><h2>Destinasi luar</h2><p>Pautan tajaan membawa anda ke laman berasingan dengan terma, syarat kelayakan dan amalan privasi sendiri. Nilai destinasi secara bebas sebelum memberi maklumat peribadi atau bayaran.</p><p class="note">Penggunaan maklumat keputusan tidak memerlukan anda mengikuti pautan tajaan.</p>`,
      zh: `<h1>推广及联盟披露</h1><p class="effective"><strong>生效日期：</strong>2026年8月24日</p><p>4DVIP88 的部分横幅和链接属于赞助或联盟链接。访客点击或在目标网站完成操作时，本站可能获得报酬。</p><h2>如何标示赞助链接</h2><p>首页广告会显示“赞助”标签，赞助链接也使用 <code>rel="sponsored"</code> 属性，以便与结果资料区分。</p><h2>获得报酬不代表什么</h2><ul><li>不会使广告商成为官方结果来源。</li><li>不代表广告商一定持牌、安全、可靠或适合所有访客。</li><li>不承诺注册批准、优惠、付款或中奖。</li><li>不代表本站已独立核实任何结果。</li></ul><h2>外部网站</h2><p>赞助链接会前往由其他机构经营的网站，该网站有自己的条款、资格规定和隐私政策。提供个人或付款资料前，请自行评估。</p><p class="note">使用结果资料并不需要点击任何赞助链接。</p>`
    },
    '/privacy.html': {
      ms: `<h1>Notis Privasi</h1><p class="effective"><strong>Tarikh berkuat kuasa:</strong> 17 September 2026</p><p>Notis ini menerangkan pengendalian maklumat apabila anda melawat my4d.co. Laman ini menyediakan keputusan untuk rujukan dan tidak menawarkan akaun pelawat, menerima pertaruhan, memproses bayaran atau meminta maklumat bank.</p><h2>Analitik dan storan pelayar</h2><p>Pada tarikh di atas, laman ini tidak memuatkan Google Analytics atau Google Tag Manager. Cloudflare menyuntik suar Web Analytics yang menghantar ukuran prestasi dan penggunaan ke <code>/cdn-cgi/rum</code>. Menurut Cloudflare, perkhidmatan itu tidak menggunakan kuki atau storan setempat untuk metrik dan tidak menjejaki pengguna individu merentasi pelanggan.</p><p>Kod laman tidak menetapkan kuki. Pilihan bahasa disimpan dalam storan setempat sebagai <code>4dvip88.language</code>. Bendera sepanduk sesi dan percubaan pautan Kamus disimpan dalam storan sesi. Nilai ini digunakan dalam pelayar dan tidak dihantar sebagai data akaun atau penukaran.</p><h2>Log pengehosan, penghantaran dan keselamatan</h2><p>Laman dihantar melalui GitHub Pages dan Cloudflare. Penyedia infrastruktur boleh memproses maklumat teknikal yang diperlukan untuk penghantaran dan perlindungan, termasuk alamat IP, masa permintaan, alamat diminta, maklumat pelayar/peranti, status respons dan peristiwa keselamatan.</p><h2>Maklumat keputusan</h2><p>Fail JSON laman yang sama mengandungi maklumat cabutan, bukan profil pelawat. Tiada rekod ahli, transaksi atau bayaran dibuat apabila anda menyemak keputusan.</p><h2>Pautan tajaan dan luar</h2><p>Laman mengandungi pautan tajaan, termasuk sepanduk BCB88 pilihan. Pada klik biasa pertama pautan navigasi Kamus dalam satu sesi tab, Kamus tetap dibuka seperti biasa tetapi terdapat 25% peluang destinasi penaja dilancarkan dalam tab baharu. Percubaan berlaku sekali sahaja bagi setiap sesi tab. Pelayar boleh menyekat atau memfokuskan tab itu. Tiada ketikan halaman lain mencetuskannya.</p><p class="note">Destinasi tajaan adalah pilihan. Jangan berikan kata laluan, maklumat bayaran atau data sensitif tanpa menilai destinasi dan berniat berurusan dengannya.</p><h2>Perubahan notis</h2><p>Notis ini akan disemak apabila ciri pengehosan, analitik, pengiklanan atau pelawat berubah. Halaman baharu akan menunjukkan tarikh berkuat kuasa yang baharu.</p>`,
      zh: `<h1>隐私声明</h1><p class="effective"><strong>生效日期：</strong>2026年9月17日</p><p>本声明说明您访问 my4d.co 时适用的资料处理方式。本站仅提供结果参考，不提供访客账户、不接受投注、不处理付款，也不要求银行资料。</p><h2>网站分析与浏览器储存</h2><p>截至上述日期，本站未加载 Google Analytics 或 Google Tag Manager。Cloudflare 会加入 Web Analytics 性能信标，将性能及使用量资料发送至同站点的 <code>/cdn-cgi/rum</code>。Cloudflare 表示该服务不会使用 Cookie 或本地储存收集指标，也不会跨客户网站追踪个人用户。</p><p>本站代码不设置 Cookie。语言选择以 <code>4dvip88.language</code> 保存在浏览器本地储存；会话横幅与号码辞典链接尝试标记保存在会话储存。这些值只在浏览器中读取，不会作为账户或转化资料发送给 my4d.co。</p><h2>托管、传输与安全日志</h2><p>本站通过 GitHub Pages 和 Cloudflare 提供服务。基础设施供应商可能处理交付和保护网站所需的技术资料，包括 IP 地址、请求时间、网址、浏览器或设备资料、响应状态和安全事件。</p><h2>结果资料</h2><p>同站点 JSON 文件只包含开彩资料，不包含访客档案。查询结果不会建立会员、交易或付款记录。</p><h2>赞助及外部链接</h2><p>本站包含赞助链接，包括可关闭的 BCB88 横幅。每个浏览器标签页会话中，首次正常点击标示的号码辞典导航链接时，号码辞典仍会正常打开，但有 25% 机会在新标签页打开同一获准赞助网站。每个标签页会话只尝试一次。浏览器可能阻止或切换到该标签页；其他页面点击不会触发此行为。</p><p class="note">赞助网站完全自愿使用。未自行评估且无意与其交易前，请勿提供密码、付款资料或其他敏感信息。</p><h2>声明变更</h2><p>网站托管、分析、广告或访客功能改变时，本声明应重新审查；更新后的页面会显示新生效日期。</p>`
    },
    '/methodology.html': {
      ms: `<h1>Panduan Data dan Kesegaran Keputusan 4D Malaysia</h1><p class="effective"><strong>Halaman dikemas kini:</strong> 3 Oktober 2026</p><p>Halaman ini menerangkan cara MY4D mengimport dan memaparkan keputusan, had semakan automatik, sebab tarikh penyedia berbeza dan rekod sejarah yang disimpan. Keputusan hanya untuk rujukan. MY4D bukan operator loteri dan tidak mendakwa hubungan dengan penyedia.</p><h2>Liputan ringkas</h2><ul><li>Penjana halaman utama menjangka sepuluh rekod yang disokong merentasi Malaysia Barat, Malaysia Timur dan Singapura.</li><li>Kad penyedia boleh mempunyai tarikh berbeza kerana jadual cabutan tidak sama.</li><li>Masa kemas kini merekodkan import yang diterima; ia bukan masa cabutan dan tidak membuktikan semua nombor muktamad atau tepat.</li><li>Arkib awam kini hanya menyenaraikan 23 dan 24 Ogos serta 5 dan 6 September 2026.</li></ul><h2>Proses paparan semasa</h2><ol><li>Skrip berjadual mengimport keputusan daripada 4d4d.co bagi penyedia yang disokong selain Grand Dragon.</li><li>Grand Dragon menggunakan suapan 4dmoon.com; sumber berbeza ini bukan semakan dua sumber bagi setiap keputusan.</li><li>Pengimport menyemak tarikh dan hari, memilih tarikh penyedia terbaru dan menyusun senarai tarikh.</li><li>Semakan penjanaan menguji set penyedia lengkap, format dan bilangan nombor, butiran cabutan berkaitan serta umur maksimum tujuh hari. Ini menguji konsistensi, bukan ketepatan rasmi.</li><li>Data diterima menjana HTML boleh dirangkak untuk halaman utama, penyedia, wilayah dan Bahasa Melayu. JavaScript menambah fungsi interaktif.</li><li>Arkib bertarikh tidak dikemas kini oleh tugas keputusan berjadual.</li></ol><h2>Sumber semasa dan kebenaran</h2><p>Kod meminta <code>https://4d4d.co/</code> dan <code>https://www.4dmoon.com/feedwest.json</code>. Pemilik laman mengesahkan bahawa pihak pengurusan memperoleh kebenaran menerbitkan semula maklumat keputusan. Tiada identiti atau kelayakan peribadi disimpan dalam repositori.</p><p class="warning"><strong>Amaran pengesahan:</strong> cap masa terkini tidak membuktikan nombor tepat, lengkap atau muktamad. Sahkan dengan penyedia berkaitan.</p><h2>Semakan automatik</h2><p>Semakan penerbitan menguji tarikh, format nombor, saiz kumpulan hadiah, butiran produk, HTML boleh dirangkak, kanonikal MY4D, tema, penanda Kamus dan set penyedia. Lulus bermaksud struktur dan kesegaran dijangka, bukan pengesahan operator.</p><h2>Pembetulan dan data lapuk</h2><p>Jika pengambilan atau semakan wajib gagal, tugas tidak menerbitkan keputusan cadangan. Laman boleh kekal pada cabutan lama. Rujuk tarikh setiap kad.</p><h2>Liputan sejarah</h2><p>Arkib keputusan lalu hanya menyenaraikan cabutan yang disimpan. Carian sejarah mengekalkan sifar hadapan dan membezakan hadiah biasa daripada jackpot, tetapi liputan berbeza mengikut penyedia dan tahun.</p><h2>Cara membaca keputusan</h2><p>Gunakan nama penyedia, tarikh khusus, nombor cabutan dan tajuk hadiah bersama. Jangan anggap keputusan lama, kamus atau kekerapan sebagai ramalan. Sahkan keputusan penting dengan penyedia.</p>`,
      zh: `<h1>马来西亚 4D 结果数据与时效指南</h1><p class="effective"><strong>页面更新：</strong>2026年10月3日</p><p>本页说明 MY4D 如何导入和显示结果、自动检查能证明及不能证明什么、为什么运营商日期可能不同，以及实际保留哪些历史记录。结果仅供参考；MY4D 不是彩票运营商，也不暗示与运营商有关联。</p><h2>覆盖概览</h2><ul><li>首页生成器预期显示马来西亚西部、东部及新加坡共十项受支持记录。</li><li>不同运营商的开彩日不同，因此卡片日期可能不一致。</li><li>更新时间只记录一次通过检查的导入，并非开彩时间，也不独立证明所有号码最终或准确。</li><li>公开存档目前仅包括 2026年8月23、24日及9月5、6日。</li></ul><h2>当前显示流程</h2><ol><li>定时脚本从 4d4d.co 导入除 Grand Dragon 外的受支持结果。</li><li>Grand Dragon 来自 4dmoon.com；使用不同来源并不代表每项结果都经过两个独立来源核对。</li><li>导入程序核对日期和星期，选择最新运营商日期并排列近期日期。</li><li>发布前检查完整运营商集合、号码格式与数量、相关开彩细节及最长七天时效。这些检查验证一致性，不证明官方准确性。</li><li>获接受的数据会生成可抓取的首页、运营商、地区及马来语 HTML；JavaScript 增加互动功能。</li><li>定时更新不会改写已保留的日期存档。</li></ol><h2>当前上游来源与授权</h2><p>代码请求 <code>https://4d4d.co/</code> 和 <code>https://www.4dmoon.com/feedwest.json</code>。网站负责人确认管理层已取得转载结果资料的许可。代码库不保存私人批准者身份或凭证。</p><p class="warning"><strong>核实警告：</strong>近期时间戳不能独立证明号码准确、完整或最终有效。重要资料请向相关运营商核实。</p><h2>自动检查项目</h2><p>发布检查包括日期、号码格式、奖项数量、相关产品资料、可抓取 HTML、MY4D canonical、主题、号码辞典标记及完整运营商集合。通过只代表结构与时效符合预期，不代表运营商核实。</p><h2>修正与过期资料</h2><p>若抓取或必要检查失败，定时任务不会发布拟议结果，网站可能继续显示较早开彩。请查看每张运营商卡片的日期。</p><h2>历史及号码搜索覆盖</h2><p>历史存档只列出本站保留的完整开彩。号码历史搜索保留前导零，并区分普通奖项与 Jackpot；覆盖范围依运营商及年份不同。</p><h2>负责任地阅读结果</h2><p>请同时核对运营商、其开彩日期、期号及奖项标题。不要把历史结果、号码辞典或出现频率视为预测。重要结果请与运营商发布资料比较。</p>`
    }
  };

  const prizeGuide = {
    ms: `<h2>Maksud label keputusan biasa</h2><p>Jadual keputusan mengenal pasti nombor mengikut kategori; ia tidak menentukan nilai tiket. Semak penyedia, produk, tarikh dan nombor cabutan sebelum membandingkan nombor.</p><table class="guide-table"><caption>Label biasa pada halaman keputusan</caption><thead><tr><th>Label</th><th>Apa yang dipaparkan</th><th>Apa yang perlu disemak</th></tr></thead><tbody><tr><th>Hadiah pertama, kedua dan ketiga</th><td>Tiga kedudukan nombor utama.</td><td>Padankan tepat termasuk sifar di hadapan.</td></tr><tr><th>Khas</th><td>Kumpulan nombor berlabel berasingan.</td><td>Jangan anggap nombor khas sebagai hadiah tiga teratas.</td></tr><tr><th>Saguhati</th><td>Satu lagi kumpulan berasingan.</td><td>Kekalkan label kategori apabila merekod.</td></tr><tr><th>3D, 5D, 6D atau lotto</th><td>Format khusus produk apabila terdapat dalam data.</td><td>Gunakan peraturan produk itu sendiri.</td></tr></tbody></table><h2>Mengapa nilai hadiah tetap tidak disenaraikan di sini</h2><p>Nilai, kelayakan dan tuntutan bergantung pada penyedia, produk, jenis tiket, taruhan, cabutan dan terma semasa. Gunakan jadual sumber dalam <a href="/play-guide/">Panduan Bayaran &amp; Permainan</a> dan sahkan dengan penyedia.</p><h2>Urutan semakan</h2><ol><li>Pilih penyedia dan produk.</li><li>Padankan tarikh dan nombor cabutan.</li><li>Bandingkan setiap digit termasuk sifar hadapan.</li><li>Kekalkan label hadiah.</li><li>Sahkan nilai dan tuntutan dengan penyedia.</li></ol><h2>Pilih keputusan penyedia</h2><ul class="page-links"><li><a href="/magnum-4d-results/">Keputusan Magnum 4D</a></li><li><a href="/sports-toto-4d-results/">Keputusan Sports Toto</a></li><li><a href="/da-ma-cai-results/">Keputusan Da Ma Cai</a></li></ul>`,
    zh: `<h2>常见结果标签的含义</h2><p>结果表按类别列出号码，本身并不决定一张票的价值。比较号码前，请确认运营商、产品、开彩日期和期号。</p><table class="guide-table"><caption>结果页常见标签</caption><thead><tr><th>标签</th><th>本站显示内容</th><th>需要核对</th></tr></thead><tbody><tr><th>头奖、二奖及三奖</th><td>该期的三个主要号码位置。</td><td>完整核对号码，包括前导零。</td></tr><tr><th>特别奖</th><td>独立标示的一组号码。</td><td>不要把特别奖当作前三奖。</td></tr><tr><th>安慰奖</th><td>另一组独立标示的号码。</td><td>记录时保留奖项类别。</td></tr><tr><th>3D、5D、6D 或 Lotto</th><td>资料中存在时显示的产品格式。</td><td>使用该产品自己的规则。</td></tr></tbody></table><h2>为何这里不直接列出固定奖金</h2><p>奖金、资格和领取规则可能取决于运营商、产品、票种、投注额、开彩及现行条款。请使用<a href="/play-guide/">奖金与玩法指南</a>中的来源表，并向运营商核实。</p><h2>谨慎核对步骤</h2><ol><li>选择票据上的运营商与产品。</li><li>核对开彩日期及期号。</li><li>逐位比较并保留前导零。</li><li>保留头奖、二奖、三奖、特别奖或安慰奖标签。</li><li>向运营商核实奖金、资格和领取详情。</li></ol><h2>选择运营商结果</h2><ul class="page-links"><li><a href="/magnum-4d-results/">Magnum 4D 结果</a></li><li><a href="/sports-toto-4d-results/">Sports Toto 结果</a></li><li><a href="/da-ma-cai-results/">Da Ma Cai 结果</a></li></ul>`
  };

  function localizeElement(element, values, html) {
    if (!element) return;
    const lang = api.getLanguage();
    const store = html ? originalHtml : originalText;
    if (!store.has(element)) store.set(element, html ? element.innerHTML : element.textContent);
    const value = lang === 'en' ? store.get(element) : values?.[lang];
    if (value == null) return;
    if (html) element.innerHTML = value;
    else element.textContent = value;
  }

  function translateCommonLeaves() {
    const lang = api.getLanguage();
    const map = common[lang] || {};
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => {
      const parent = node.parentElement;
      if (!parent || /^(SCRIPT|STYLE|NOSCRIPT|CODE)$/.test(parent.tagName) || parent.closest('[data-i18n],[data-i18n-html]')) return;
      if (!originalText.has(node)) originalText.set(node, node.nodeValue);
      const original = originalText.get(node);
      const base = original.trim();
      if (lang === 'en') { node.nodeValue = original; return; }
      if (map[base]) node.nodeValue = original.replace(base, map[base]);
    });
    document.querySelectorAll('a,button,option,th,td,caption,summary,strong,h1,h2,h3,small,label>span').forEach(el => {
      if (el.dataset.i18n || el.closest('[data-i18n-html]')) return;
      if (!originalText.has(el)) originalText.set(el, el.textContent);
      const base = originalText.get(el).trim();
      if (lang === 'en') { el.textContent = originalText.get(el); return; }
      if (map[base]) el.textContent = map[base];
    });
    document.querySelectorAll('[data-language-label]').forEach(el => { el.textContent = lang === 'zh' ? '语言' : lang === 'ms' ? 'Bahasa' : 'Language'; });
    const theme = document.querySelector('[data-theme-control]');
    if (theme) {
      const label = theme.querySelector('span');
      const opts = theme.querySelectorAll('option');
      if (label) label.textContent = lang === 'zh' ? '主题' : lang === 'ms' ? 'Tema' : 'Theme';
      const text = lang === 'zh' ? ['跟随系统','浅色','深色'] : lang === 'ms' ? ['Sistem','Cerah','Gelap'] : ['System','Light','Dark'];
      opts.forEach((opt, index) => { opt.textContent = text[index]; });
    }
  }

  function translateDynamicResults() {
    const lang = api.getLanguage();
    document.querySelectorAll('.result-meta').forEach(el => {
      if (!originalText.has(el)) originalText.set(el, el.textContent);
      const base = originalText.get(el);
      if (lang === 'en') { el.textContent = base; return; }
      el.textContent = base.replace(/^Draw date:/, lang === 'zh' ? '开彩日期：' : 'Tarikh cabutan:').replace(/ · Draw /, lang === 'zh' ? ' · 期号 ' : ' · Cabutan ');
    });
    document.querySelectorAll('.status-box p').forEach(el => {
      if (!originalHtml.has(el)) originalHtml.set(el, el.innerHTML);
      const base = originalHtml.get(el);
      if (lang === 'en') { el.innerHTML = base; return; }
      el.innerHTML = base
        .replace('Most recent provider draw shown:', lang === 'zh' ? '显示的最新运营商开彩：' : 'Cabutan penyedia terkini dipaparkan:')
        .replace('Data file updated:', lang === 'zh' ? '数据文件更新时间：' : 'Fail data dikemas kini:')
        .replace('Retained data imported:', lang === 'zh' ? '保留数据导入时间：' : 'Data tersimpan diimport:')
        .replace('Use this as a reference and verify important results with the relevant provider.', lang === 'zh' ? '本页仅供参考；重要结果请向相关运营商核实。' : 'Gunakan sebagai rujukan dan sahkan keputusan penting dengan penyedia berkaitan.');
    });
  }

  function translateHome() {
    if (location.pathname !== '/') return;
    const sections = document.querySelectorAll('.footsec');
    const headingKeys = ['homeLatest','homeCompare',null,'homeWhen','homeDisclaimer'];
    const paragraphKeys = ['homeP1','homeP2','homeP3','homeP4','homeP5'];
    sections.forEach((section, index) => {
      const h = section.querySelector('h3'); const p = section.querySelector('p');
      if (h && headingKeys[index]) h.textContent = api.t(headingKeys[index]);
      if (p && paragraphKeys[index]) p.innerHTML = api.t(paragraphKeys[index]);
    });
  }

  function translateLegal() {
    const entry = legal[location.pathname];
    if (!entry) return;
    localizeElement(document.querySelector('article'), entry, true);
  }

  const providerPaths = new Set(['/magnum-4d-results/','/sports-toto-4d-results/','/da-ma-cai-results/','/sabah-88-4d-results/','/special-cash-sweep-results/','/sandakan-stc-4d-results/']);
  function translateProviderPage() {
    if (!providerPaths.has(location.pathname)) return;
    const lang = api.getLanguage();
    const hero = document.querySelector('.page-hero');
    const h1 = hero?.querySelector('h1');
    if (!h1) return;
    if (!originalText.has(h1)) originalText.set(h1, h1.textContent);
    const provider = originalText.get(h1).replace(/ Results$/, '');
    const lead = hero.querySelector('.lead');
    localizeElement(h1,{ms:`Keputusan ${provider}`,zh:`${provider} 开彩结果`});
    localizeElement(lead,{ms:`Lihat cabutan ${provider} lengkap terkini yang tersedia di laman rujukan bebas ini, bersama tarikh cabutan dan masa kemas kini.`,zh:`查看本独立参考网站提供的最新完整 ${provider} 开彩结果、开彩日期及更新时间。`});
    const cards = document.querySelectorAll('.content-card');
    if (cards.length < 2 || lang === 'en') { if (cards[1] && originalHtml.has(cards[1])) cards[1].innerHTML=originalHtml.get(cards[1]); return; }
    if (!originalHtml.has(cards[1])) originalHtml.set(cards[1], cards[1].innerHTML);
    const region = ['/magnum-4d-results/','/sports-toto-4d-results/','/da-ma-cai-results/'].includes(location.pathname) ? '/west-malaysia-4d-results/' : '/east-malaysia-4d-results/';
    cards[1].innerHTML = lang === 'zh'
      ? `<h2>本结果页的范围</h2><p>本页显示所列开彩的 ${provider} 号码。请把每个奖项标题与号码一起阅读，并核对开彩日期和期号。</p><h2>如何阅读及核实</h2><p>比较号码前先核对日期和期号。前导零具有意义，特别奖或安慰奖不能当作前三奖。</p><p>依赖结果前，请把日期、期号及奖项与运营商发布的资料比较。MY4D 是独立参考网站，并非 ${provider} 官方来源。</p><p><a href="${region}">比较相关地区的当前运营商结果</a></p><p><a href="/methodology.html">阅读来源、时效与修正方法。</a></p>`
      : `<h2>Liputan halaman keputusan ini</h2><p>Halaman ini memaparkan nombor ${provider} bagi cabutan yang dinyatakan. Baca tajuk hadiah bersama nombornya, kemudian padankan tarikh dan nombor cabutan.</p><h2>Cara membaca dan mengesahkan</h2><p>Padankan tarikh dan nombor cabutan dahulu. Sifar di hadapan penting; hadiah khas atau saguhati bukan hadiah tiga teratas.</p><p>Sebelum bergantung pada keputusan, bandingkan tarikh, nombor cabutan dan kategori hadiah dengan terbitan penyedia. MY4D ialah laman bebas, bukan sumber rasmi ${provider}.</p><p><a href="${region}">Bandingkan keputusan penyedia serantau semasa</a></p><p><a href="/methodology.html">Baca kaedah sumber, kesegaran dan pembetulan.</a></p>`;
  }

  function translateRegionPage() {
    if (!['/west-malaysia-4d-results/','/east-malaysia-4d-results/'].includes(location.pathname)) return;
    const lang = api.getLanguage(); const west = location.pathname.startsWith('/west');
    const hero = document.querySelector('.page-hero');
    localizeElement(hero?.querySelector('h1'),{ms:`Keputusan 4D Malaysia ${west?'Barat':'Timur'}`,zh:`${west?'西马':'东马'} 4D 开彩结果`});
    localizeElement(hero?.querySelector('.lead'),{ms:west?'Bandingkan keputusan lengkap terkini Magnum 4D, Sports Toto dan Da Ma Cai.':'Bandingkan keputusan lengkap terkini Sabah 88, Sandakan STC dan Special Cash Sweep.',zh:west?'比较 Magnum 4D、Sports Toto 与 Da Ma Cai 的最新完整结果。':'比较 Sabah 88、Sandakan STC 与 Special Cash Sweep 的最新完整结果。'});
    const cards=document.querySelectorAll('.content-card'); if(cards.length<2)return;
    if(lang==='en'){if(originalHtml.has(cards[1]))cards[1].innerHTML=originalHtml.get(cards[1]);return} if(!originalHtml.has(cards[1]))originalHtml.set(cards[1],cards[1].innerHTML);
    const names=west?'Magnum、Sports Toto 与 Da Ma Cai':'Sabah 88、Sandakan STC 与 Special Cash Sweep';
    cards[1].innerHTML=lang==='zh'?`<h2>地区页面范围</h2><p>本页把 ${names} 分开比较，不会把它们当成同一场开彩。每家运营商保留自己的日期、期号和奖项。</p><h2>如何比较</h2><p>先看运营商标题，再比较日期和期号。即使日期相同，也仍是各自独立开彩。依赖号码前，请分别向相关运营商核实。</p>`:`<h2>Liputan halaman serantau</h2><p>Halaman ini membandingkan penyedia berkaitan secara berasingan dan tidak menganggapnya satu cabutan. Setiap penyedia mengekalkan tarikh, nombor cabutan dan kategori hadiah sendiri.</p><h2>Cara membandingkan</h2><p>Mulakan dengan tajuk penyedia, kemudian tarikh dan nombor cabutan. Walaupun tarikh sama, cabutan adalah berasingan. Sahkan setiap keputusan dengan penyedia sebelum bergantung padanya.</p>`;
  }

  function translateArchivePages() {
    const lang=api.getLanguage();
    if(location.pathname==='/past-results/'){
      const hero=document.querySelector('.page-hero'); localizeElement(hero?.querySelector('h1'),{ms:'Keputusan 4D Malaysia Lepas',zh:'马来西亚 4D 历史结果'}); localizeElement(hero?.querySelector('.lead'),{ms:'Lihat arkib keputusan lengkap yang disimpan oleh laman ini.',zh:'浏览本站保留的完整开彩结果存档。'});
    }
    if(/^\/results\/\d{4}-\d{2}-\d{2}\/$/.test(location.pathname)){
      const h1=document.querySelector('.page-hero h1'); if(h1&&!originalText.has(h1))originalText.set(h1,h1.textContent); const base=originalText.get(h1)||''; const date=base.replace(/^Malaysia 4D Results:\s*/, ''); localizeElement(h1,{ms:`Keputusan 4D Malaysia: ${date}`,zh:`马来西亚 4D 结果：${date}`});
      localizeElement(document.querySelector('.page-hero .lead'),{ms:'Arkib yang hanya mengandungi keputusan penyedia bagi tarikh cabutan ini.',zh:'本存档只包含记录为此开彩日期的运营商结果。'});
      const cards=document.querySelectorAll('.content-card'); if(cards.length>1&&lang!=='en'){if(!originalHtml.has(cards[1]))originalHtml.set(cards[1],cards[1].innerHTML);cards[1].innerHTML=lang==='zh'?`<h2>存档范围</h2><p>本页只包含本站保留且运营商自身开彩日期与网址日期相符的记录。不同日期的运营商不会被重新标示来填满页面。</p><p>日期存档不会由当前结果定时任务更新。重要历史号码请向相关运营商核实；修正需要保留来源证据和人工复核。</p><p><a href="/past-results/">浏览现有历史结果。</a></p>`:`<h2>Liputan arkib</h2><p>Halaman ini hanya mengandungi rekod tersimpan yang tarikh cabutan penyedianya sepadan dengan tarikh URL. Penyedia bertarikh lain tidak dilabel semula untuk melengkapkan halaman.</p><p>Arkib bertarikh tidak dikemas kini oleh tugas keputusan semasa. Sahkan nombor sejarah penting dengan penyedia; pembetulan memerlukan bukti sumber dan semakan manual.</p><p><a href="/past-results/">Lihat keputusan lepas yang tersedia.</a></p>`;} else if(cards.length>1&&originalHtml.has(cards[1]))cards[1].innerHTML=originalHtml.get(cards[1]);
    }
  }

  function translatePrizeGuide() {
    if(location.pathname!=='/4d-prize-guide/')return;
    const lang=api.getLanguage(); localizeElement(document.querySelector('.page-hero h1'),{ms:'Panduan Hadiah 4D Malaysia',zh:'马来西亚 4D 奖项指南'}); localizeElement(document.querySelector('.page-hero .lead'),{ms:'Panduan fakta untuk label biasa dalam jadual keputusan 4D.',zh:'说明 4D 结果表常见标签的事实指南。'});
    const card=document.querySelector('.content-card'); if(!card)return; if(!originalHtml.has(card))originalHtml.set(card,card.innerHTML); card.innerHTML=lang==='en'?originalHtml.get(card):prizeGuide[lang];
  }

  function translateGuideDetails() {
    if(location.pathname!=='/play-guide/')return;
    const lang=api.getLanguage();
    const pairs=[
      ['.page-title>p:last-child','Semak rujukan hadiah bersumber dan berlatih membaca slip. Halaman ini tidak menerima pertaruhan, meramal keputusan atau menjamin pulangan.','查看有来源支持的奖金参考，并练习阅读注单。本站不接受投注、不预测结果，也不保证回报。'],
      ['#payout-table>p','Nilai di bawah ialah hadiah diterbitkan bagi setiap taruhan straight RM1 oleh Magnum 4D, Sports Toto dan Da Ma Cai. Nama produk berbeza: Da Ma Cai menggunakan “ABC” untuk Big dan “A” untuk Small.','以下数值是 Magnum 4D、Sports Toto 和 Da Ma Cai 公布的每 RM1 Straight 投注奖金。产品名称不同：Da Ma Cai 将 Big 称为“ABC”，Small 称为“A”。'],
      ['.ibox-details>p','Jumlah IBOX bergantung pada bilangan susunan unik dalam nombor yang dipilih. Nilai ini ialah hadiah diterbitkan bagi permainan IBOX/i-Perm minimum RM1.','IBOX 金额取决于所选号码的不同排列数量。这些数值是最低 RM1 IBOX/i-Perm 玩法的已公布奖金。'],
      ['.source-box>p','Jumlah dan peraturan boleh berubah. Sahkan peraturan semasa dan tiket bercetak dengan penyedia sebelum bergantung pada sebarang angka. MY4D bebas daripada penyedia ini.','金额与规则可能改变。依赖任何数值前，请向运营商核实现行规则及纸本票据。MY4D 与这些运营商相互独立。'],
      ['#how-to-bet .step-grid li:nth-child(1) p','Mulakan dengan operator dan produk pada slip permainan.','从注单所列的运营商和产品开始。'],
      ['#how-to-bet .step-grid li:nth-child(2) p','Gunakan tepat empat digit dari 0000 hingga 9999, termasuk sifar di hadapan.','输入 0000 至 9999 的四位数字，包括前导零。'],
      ['#how-to-bet .step-grid li:nth-child(3) p','Straight mengekalkan satu susunan. IBOX/i-Perm meliputi susunan unik mengikut peraturan penyedia.','Straight 保持一个顺序；IBOX/i-Perm 按运营商规则覆盖号码的不同排列。'],
      ['#how-to-bet .step-grid li:nth-child(4) p','Big meliputi tiga hadiah teratas, khas/permulaan dan saguhati. Small hanya meliputi tiga teratas dengan hadiah diterbitkan lebih tinggi.','Big 包括前三奖、特别/入围奖及安慰奖；Small 只包括前三奖，但公布的奖金较高。'],
      ['#how-to-bet .step-grid li:nth-child(5) p','Semak nombor, penyedia, cabutan, jenis permainan, pilihan dan jumlah pada tiket sebenar.','检查真实票据上的号码、运营商、开彩、玩法、类别和金额。'],
      ['#number-help','Borang ini ialah pratonton pendidikan. Ia tidak menghantar atau menyimpan apa-apa.','此表单仅供教学预览，不会发送或储存任何资料。'],
      ['.caution-card p','Panduan ini menerangkan struktur diterbitkan dan bukan nasihat pertaruhan. Ia tidak mengira bayaran terjamin, mengesahkan kelayakan tiket atau menggantikan peraturan penyedia. Perjudian melibatkan risiko kewangan. Hanya sertai jika sah dan dibenarkan, serta tetapkan had perbelanjaan.','本指南说明已公布的结构，并非投注建议。它不会计算保证奖金、核实票据资格或取代运营商规则。赌博涉及财务风险；只应在合法及获准的情况下参与，并设定严格预算。']
    ];
    pairs.forEach(([selector,ms,zh])=>localizeElement(document.querySelector(selector),{ms,zh}));
    document.querySelectorAll('.source-box li a').forEach((a,i)=>{const ms=['Struktur hadiah Magnum 4D (PDF)','Struktur hadiah Sports Toto','Cara bermain dan struktur hadiah Da Ma Cai'][i];const zh=['Magnum 4D 奖金结构（PDF）','Sports Toto 奖金结构','Da Ma Cai 玩法及奖金结构'][i];localizeElement(a,{ms,zh});});
  }

  function apply() {
    translateCommonLeaves();
    translateDynamicResults();
    translateHome();
    translateLegal();
    translateProviderPage();
    translateRegionPage();
    translateArchivePages();
    translatePrizeGuide();
    translateGuideDetails();
    const lang=api.getLanguage();
    document.title = lang !== 'en' && document.querySelector('main h1') ? `${document.querySelector('main h1').textContent} | MY4D` : originalTitle;
  }

  window.SitePagesLocale=Object.freeze({apply});
  document.addEventListener('site-language-change',apply);
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',apply);else apply();
})();
