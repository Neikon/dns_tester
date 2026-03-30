application_id = 'es.neikon.dns_tester'

scalable_dir = 'hicolor' / 'scalable' / 'apps'
install_data(
  scalable_dir / ('@0@.svg').format(application_id),
  install_dir: get_option('datadir') / 'icons' / scalable_dir
)

provider_icons = files(
  scalable_dir / 'es.neikon.dns_tester-provider-adguard.svg',
  scalable_dir / 'es.neikon.dns_tester-provider-cloudflare.svg',
  scalable_dir / 'es.neikon.dns_tester-provider-controld.svg',
  scalable_dir / 'es.neikon.dns_tester-provider-dns4eu.svg',
  scalable_dir / 'es.neikon.dns_tester-provider-flashstart.svg',
  scalable_dir / 'es.neikon.dns_tester-provider-gcore.svg',
  scalable_dir / 'es.neikon.dns_tester-provider-google.svg',
  scalable_dir / 'es.neikon.dns_tester-provider-mullvad.svg',
  scalable_dir / 'es.neikon.dns_tester-provider-nextdns.svg',
  scalable_dir / 'es.neikon.dns_tester-provider-quad9.svg',
)
install_data(
  provider_icons,
  install_dir: get_option('datadir') / 'icons' / scalable_dir
)

symbolic_dir = 'hicolor' / 'symbolic' / 'apps'
install_data(
  symbolic_dir / ('@0@-symbolic.svg').format(application_id),
  install_dir: get_option('datadir') / 'icons' / symbolic_dir
)
